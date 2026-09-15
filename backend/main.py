"""Serveur de l'application Botanik.

Expose l'etat des capteurs et sert le frontend compile.

ATTENTION a l'ordre des declarations : le montage des fichiers statiques se
fait sur "/" et intercepte donc tout. Les routes /api doivent imperativement
etre declarees AVANT, sinon elles ne sont jamais atteintes.
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth
import bus
import registre
import systeme
from config import DB_URL, INTERVALLE_S, TOPIC_COMMANDES

RACINE = Path(__file__).parent.parent
DIST = RACINE / "frontend" / "dist"
SAUVEGARDES = RACINE / "sauvegardes"

# Au-dela, l'archivage est considere comme interrompu. Trois cycles de
# publication laissent passer un retard ponctuel sans crier au loup ; le
# plancher couvre le cas d'un intervalle tres court.
RETARD_TOLERE_S = max(30, 3 * INTERVALLE_S)

# Fenetres proposees par le dashboard, et le pas d'agregation associe.
# Sans regroupement, un mois de mesures a la minute ferait 43 000 points
# pour quelques centaines de pixels.
FENETRES = {
    "1j": ("1 day", "10 minutes"),
    "1s": ("7 days", "2 hours"),
    "1m": ("30 days", "8 hours"),
}

HISTORIQUE = """
    SELECT date_bin(%s::interval, ts, TIMESTAMPTZ '2000-01-01') AS t,
           avg(valeur) AS v
    FROM mesures
    WHERE capteur = %s AND ts >= now() - %s::interval
    GROUP BY t
    ORDER BY t
"""

# Derniere valeur connue de chaque capteur, en une seule requete.
DERNIERES = """
    SELECT DISTINCT ON (capteur) capteur, valeur, unite, ts
    FROM mesures
    ORDER BY capteur, ts DESC
"""

def base():
    """Connexion courte. A cette echelle, ouvrir a la demande coute moins
    cher a maintenir qu'un pool, et evite les connexions mortes."""
    try:
        return psycopg.connect(DB_URL, connect_timeout=5, autocommit=True)
    except psycopg.Error as e:
        raise HTTPException(503, f"base de donnees injoignable : {e}") from e


def interroger(requete, params=()):
    """Execute une lecture et renvoie les lignes.

    Une base injoignable devient un 503 et non un 500 : c'est une panne
    d'infrastructure, pas une faute du client -- et le dashboard doit
    pouvoir faire la difference.
    """
    try:
        with base() as conn, conn.cursor() as cur:
            cur.execute(requete, params)
            return cur.fetchall()
    except psycopg.Error as e:
        raise HTTPException(503, f"base de donnees injoignable : {e}") from e


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    """Le schema d'authentification se cree au demarrage et non dans
    init.sql : ce dernier n'est joue qu'a la creation du volume, donc
    jamais sur une base deja en place."""
    try:
        with base() as conn:
            neuf = auth.preparer(conn)
        if neuf:
            identifiant, mdp = neuf
            print(
                "  Compte cree - identifiant : "
                + identifiant + "   mot de passe : " + mdp,
                flush=True,
            )
    except HTTPException as e:
        print(f"Authentification non initialisee : {e.detail}", flush=True)

    bus.demarrer()
    yield
    bus.arreter()


app = FastAPI(title="Botanik", lifespan=cycle_de_vie)


@app.get("/api/capteurs")
def capteurs():
    """Les capteurs actifs, chacun avec sa derniere mesure si elle existe."""
    dernieres = {
        capteur: {"valeur": valeur, "unite": unite, "ts": ts.isoformat()}
        for capteur, valeur, unite, ts in interroger(DERNIERES)
    }

    return [
        {
            "id": c["id"],
            "libelle": c["libelle"],
            "unite": c["unite"],
            "ideal": c["ideal"],
            "echelle": c["echelle"],
            # None tant qu'aucune mesure n'est arrivee pour ce capteur
            "mesure": dernieres.get(c["id"]),
        }
        for c in registre.capteurs_actifs()
    ]


@app.get("/api/mesures")
def mesures(capteur: str, fenetre: str = "1j"):
    """Historique d'un capteur, agrege selon la fenetre demandee."""
    if fenetre not in FENETRES:
        raise HTTPException(400, f"fenetre inconnue : {fenetre}")
    duree, pas = FENETRES[fenetre]

    if not any(c["id"] == capteur for c in registre.capteurs_actifs()):
        raise HTTPException(404, f"capteur inconnu ou inactif : {capteur}")

    points = [
        {"ts": t.isoformat(), "valeur": round(float(v), 2)}
        for t, v in interroger(HISTORIQUE, (pas, capteur, duree))
    ]
    return {"capteur": capteur, "fenetre": fenetre, "points": points}


# Sans nouvelle pendant ce delai, on envoie un commentaire SSE. Il ne sert
# a rien cote navigateur, mais il fait echouer l'ecriture si la connexion
# est morte -- seule facon de s'en apercevoir et de liberer la file.
BATTEMENT_S = 20


@app.get("/api/flux")
async def flux():
    """Flux des mesures, poussees a l'instant ou elles sont publiees.

    Pourquoi une poussee ici alors que les courbes s'interrogent : ce ne
    sont pas les memes besoins. Une courbe demande un historique agrege,
    calcule par la base a chaque appel ; une valeur du moment n'a rien a
    calculer, elle doit juste arriver vite. Interroger pour l'obtenir
    ajoutait jusqu'a cinq secondes de retard pour rien.

    Le flux ne porte que les mesures qui arrivent : l'etat initial de
    l'ecran vient de /api/capteurs, qui lit la derniere ligne en base.
    """
    async def evenements():
        file = bus.abonner()
        try:
            while True:
                try:
                    mesure = await asyncio.wait_for(file.get(), BATTEMENT_S)
                except asyncio.TimeoutError:
                    yield ": battement\n\n"
                    continue
                yield f"data: {json.dumps(mesure)}\n\n"
        finally:
            # Atteint aussi quand le navigateur se ferme : Starlette
            # annule le generateur, et la file doit partir avec lui.
            bus.desabonner(file)

    return StreamingResponse(
        evenements(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sante")
def sante():
    """Sante de la chaine d'archivage.

    Depuis que les bulles recoivent les mesures par le flux MQTT, un
    collecteur arrete ne se voit plus a l'ecran : les valeurs continuent
    de defiler alors que plus rien n'est enregistre. Or c'est cette base
    qui porte l'historique de germination et le jeu de donnees du modele.
    Une panne silencieuse de plusieurs jours y serait irrattrapable.

    Les deux ages sont calcules ici, et non dans le navigateur : ils se
    comparent a l'horloge de la machine qui ecrit, pas a celle de qui
    regarde -- un telephone mal regle donnerait sinon de fausses alertes.
    """
    lignes = interroger("SELECT max(ts) FROM mesures")
    derniere = lignes[0][0] if lignes else None
    archivage_s = (
        round((datetime.now(timezone.utc) - derniere).total_seconds())
        if derniere else None
    )

    # Age de la sauvegarde la plus recente, en heures.
    archives = sorted(SAUVEGARDES.glob("botanik-*.sql.gz")) if SAUVEGARDES.is_dir() else []
    sauvegarde_h = (
        round((time.time() - max(a.stat().st_mtime for a in archives)) / 3600, 1)
        if archives else None
    )

    return {
        "archivage_s": archivage_s,
        "archivage_ok": archivage_s is not None and archivage_s <= RETARD_TOLERE_S,
        "sauvegarde_h": sauvegarde_h,
    }


@app.get("/api/systeme")
def etat_systeme():
    """Sante de la machine : un sujet distinct de celui de la serre."""
    return systeme.etat()


class Identifiants(BaseModel):
    identifiant: str
    mot_de_passe: str


@app.post("/api/connexion")
def connexion(corps: Identifiants, reponse: Response):
    with base() as conn:
        jeton = auth.ouvrir_session(conn, corps.identifiant, corps.mot_de_passe)
    if not jeton:
        raise HTTPException(401, "identifiant ou mot de passe incorrect")

    # httponly : le jeton reste hors de portee du JavaScript de la page,
    # ce qui le protege d'une injection de script.
    reponse.set_cookie(
        "botanik_session", jeton,
        httponly=True, samesite="lax", max_age=7 * 24 * 3600,
    )
    return {"identifiant": corps.identifiant}


@app.post("/api/deconnexion")
def deconnexion(reponse: Response, botanik_session: str | None = Cookie(default=None)):
    with base() as conn:
        auth.fermer_session(conn, botanik_session)
    reponse.delete_cookie("botanik_session")
    return {"ok": True}


@app.get("/api/moi")
def moi(botanik_session: str | None = Cookie(default=None)):
    """Qui est connecte. Le frontend s'en sert pour decider s'il affiche
    le pilotage -- la verification reelle se fait a chaque commande."""
    with base() as conn:
        identifiant = auth.compte_de(conn, botanik_session)
    return {"identifiant": identifiant}


@app.get("/api/actionneurs")
def actionneurs():
    """Les actionneurs actifs, chacun avec l'etat qu'il a lui-meme annonce.

    `valeur` a None signifie que l'actionneur ne s'est pas manifeste --
    service arrete, ou broker injoignable. Le dashboard doit pouvoir
    montrer cette difference : ne pas savoir n'est pas la meme chose
    qu'etre a l'arret.
    """
    connus = bus.etats()
    return [
        {
            "id": a["id"],
            "libelle": a["libelle"],
            "detail": a["detail"],
            "valeur": connus.get(a["id"], {}).get("valeur"),
            "ts": connus.get(a["id"], {}).get("ts"),
        }
        for a in registre.actionneurs_actifs()
    ]


class Commande(BaseModel):
    actionneur: str
    valeur: float


@app.post("/api/commandes")
def commander(
    corps: Commande, botanik_session: str | None = Cookie(default=None),
):
    """Emet une commande manuelle vers l'actionneur, puis la consigne.

    Reservee aux comptes connectes : masquer le bouton cote navigateur ne
    protege rien.

    L'ordre compte. La commande part d'abord sur MQTT ; elle n'est ecrite
    en base que si le broker l'a prise. `commandes` est ainsi le journal
    de ce qui a REELLEMENT ete emis, et non de ce qu'on a souhaite -- une
    distinction qui comptera le jour ou l'IA relira cet historique pour
    apprendre l'effet de ses propres actions.
    """
    with base() as conn:
        identifiant = auth.compte_de(conn, botanik_session)
        if not identifiant:
            raise HTTPException(401, "connexion requise")

        topic = f"{TOPIC_COMMANDES}/{corps.actionneur}"
        if not bus.publier(topic, {"valeur": corps.valeur, "source": "manuel"}):
            raise HTTPException(503, "broker MQTT injoignable")

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO commandes (actionneur, valeur, source) "
                "VALUES (%s, %s, 'manuel')",
                (corps.actionneur, corps.valeur),
            )
    return {"ok": True, "par": identifiant, "topic": topic}


# ---- le service du frontend doit rester en dernier ----
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{chemin:path}")
    def frontend(chemin: str):
        """Sert un fichier s'il existe, sinon index.html.

        Le routage de l'application vit dans le navigateur : le serveur ne
        connait ni /historique ni les routes a venir. Sans ce repli, un
        rafraichissement sur l'une d'elles renverrait un 404.
        """
        fichier = DIST / chemin
        if chemin and fichier.is_file():
            return FileResponse(fichier)
        return FileResponse(DIST / "index.html")
else:
    # Pas bloquant : en developpement le front est servi par Vite sur :5173,
    # et l'API doit pouvoir tourner seule.
    print(f"Frontend non compile ({DIST}) -- seules les routes /api repondent")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
