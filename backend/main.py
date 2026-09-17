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

import numpy as np

import auth
import bdd
import bus
import decision
import donnees
import eclairement
import poids as magasin
import registre
import schema
import seuils
import systeme
import verrous
from config import ARCHIVAGE_S, TOPIC_COMMANDES
from drivers import DRIVERS, SORTIES

RACINE = Path(__file__).parent.parent
DIST = RACINE / "frontend" / "dist"
SAUVEGARDES = RACINE / "sauvegardes"

# Au-dela, l'archivage est considere comme interrompu.
#
# La reference est la cadence d'ARCHIVAGE et non celle de lecture : c'est
# l'age de la derniere ligne EN BASE qu'on mesure ici. Depuis que les
# deux sont decouplees, une mesure fraiche de 200 secondes est parfaitement
# normale -- la comparer a la cadence de lecture ferait clignoter le
# temoin en permanence.
RETARD_TOLERE_S = max(30, 2.5 * ARCHIVAGE_S)

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
    """La connexion de `bdd`, dont l'echec devient une reponse HTTP.

    C'est la seule difference entre l'API et les services de fond : une
    base injoignable n'est pas une faute du client, elle merite un 503
    que le dashboard sait interpreter."""
    try:
        return bdd.connexion()
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
            schema.preparer(conn)
            neuf = auth.compte_initial(conn)
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
    """Les capteurs actifs, chacun avec sa derniere mesure connue.

    `simule` distingue une vraie sonde d'une valeur inventee. Le materiel
    arrive par morceaux : tant que tout n'est pas cable, l'ecran melange
    les deux, et il doit le dire. Le calcul passe par le MEME resolveur
    que le publisher, donc l'ecran ne peut pas annoncer une sonde reelle
    la ou le service lit du simule.
    """
    # La base d'abord -- elle survit a un redemarrage de l'API -- puis ce
    # que le flux vient de pousser, qui est plus frais de plusieurs
    # minutes depuis que l'archivage est espace. Cette route et le flux
    # doivent raconter la meme chose.
    dernieres = {
        capteur: {"valeur": valeur, "unite": unite, "ts": ts.isoformat()}
        for capteur, valeur, unite, ts in interroger(DERNIERES)
    }
    vivantes = bus.mesures()
    dernieres.update({
        capteur: {"valeur": m["valeur"], "unite": m.get("unite"), "ts": m["ts"]}
        for capteur, m in vivantes.items()
    })

    actifs = registre.capteurs_actifs()
    resolus = registre.resoudre(actifs, DRIVERS)

    def simulee(identifiant: str) -> bool:
        """La mesure en cours fait foi, le registre ne sert que d'attente.

        Le registre dit ce qu'on a DECIDE de lire ; la mesure dit ce
        qu'on a REUSSI a lire. Une sonde debranchee en cours de route
        n'apparait que dans la seconde.
        """
        vivante = vivantes.get(identifiant)
        if vivante is not None and "simule" in vivante:
            return bool(vivante["simule"])
        return resolus.get(identifiant, {}).get("source") == "simule"

    return [
        {
            "id": c["id"],
            "libelle": c["libelle"],
            "unite": c["unite"],
            "ideal": c["ideal"],
            "echelle": c["echelle"],
            "simule": simulee(c["id"]),
            # None tant qu'aucune mesure n'est arrivee pour ce capteur
            "mesure": dernieres.get(c["id"]),
        }
        for c in actifs
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


# Le modele est relu de temps en temps plutot qu'a chaque appel : 67
# parametres ne coutent rien a garder, et un reentrainement prend effet
# sans redemarrer l'API.
RELECTURE_MODELE_S = 300
_modele: dict = {"relu": 0.0}


def modele_courant():
    """Poids et metadonnees du modele, ou None si aucun n'est entraine."""
    if time.time() - _modele["relu"] < RELECTURE_MODELE_S and "poids" in _modele:
        return _modele.get("poids"), _modele.get("meta"), _modele.get("version")
    try:
        with base() as conn:
            charge = magasin.charger(conn)
    except HTTPException:
        return None, None, None
    _modele.update(relu=time.time())
    if charge is None:
        _modele.update(poids=None, meta=None, version=None)
        return None, None, None
    p, meta, version = charge
    _modele.update(poids=p, meta=meta, version=version)
    return p, meta, version


def _nom_alerte(grandeur: str, cote: str) -> dict:
    """Libelle et gravite d'une alerte, depuis les regles du domaine."""
    return decision.ALERTES.get((grandeur, cote),
                                {"libelle": f"{grandeur} {cote}", "humaine": False})


@app.get("/api/alertes")
def alertes():
    """Ce qui ne va pas en ce moment.

    Une alerte reste ouverte tant que le probleme dure, meme si la serre
    est deja en train d'y remedier : la pompe tourne, mais le sol est
    encore trop sec. C'est bien ce qu'on veut voir -- le probleme, et le
    fait qu'il soit pris en charge.
    """
    lignes = interroger(
        "SELECT grandeur, cote, debut FROM alertes WHERE fin IS NULL "
        "ORDER BY debut"
    )
    return [
        {"grandeur": grandeur, "cote": cote, "depuis": debut.isoformat(),
         **_nom_alerte(grandeur, cote)}
        for grandeur, cote, debut in lignes
    ]


@app.get("/api/evenements")
def evenements(limite: int = 40):
    """Journal melant les commandes et les alertes, du plus recent au plus
    ancien.

    Les deux dans le meme flux, parce qu'ils se lisent ensemble : « sol
    trop sec detecte », puis « arrosage active », puis « sol trop sec
    leve ». Separes en deux listes, la causalite disparaitrait.

    `source` dit qui a decide d'une commande : la main de l'utilisateur,
    le modele, ou le garde-fou de securite.
    """
    limite = max(1, min(limite, 200))

    commandes = [
        {"genre": "commande", "ts": ts.isoformat(), "sujet": actionneur,
         "valeur": float(valeur), "source": source}
        for ts, actionneur, valeur, source in interroger(
            "SELECT ts, actionneur, valeur, source FROM commandes "
            "ORDER BY ts DESC LIMIT %s", (limite,))
    ]

    # Chaque episode donne deux evenements : son ouverture, et sa cloture
    # quand elle a eu lieu. UNION plutot que deux requetes : la limite
    # doit s'appliquer au melange, pas a chaque source.
    alertes_brutes = interroger(
        """
        SELECT ts, grandeur, cote, ouverture FROM (
            SELECT debut AS ts, grandeur, cote, true  AS ouverture FROM alertes
            UNION ALL
            SELECT fin   AS ts, grandeur, cote, false AS ouverture FROM alertes
            WHERE fin IS NOT NULL
        ) t ORDER BY ts DESC LIMIT %s
        """,
        (limite,),
    )
    evenements_alertes = [
        {"genre": "alerte", "ts": ts.isoformat(), "sujet": grandeur,
         "cote": cote, "ouverture": ouverture, **_nom_alerte(grandeur, cote)}
        for ts, grandeur, cote, ouverture in alertes_brutes
    ]

    tout = commandes + evenements_alertes
    tout.sort(key=lambda e: e["ts"], reverse=True)
    return tout[:limite]


@app.get("/api/modele")
def modele():
    """Le reseau entraine, et les seuils qu'il applique en ce moment.

    Les seuils ne sont pas stockes : ils sont RELUS dans le reseau a
    chaque appel, en balayant chaque grandeur aux conditions du moment.
    C'est pour cela qu'ils se deplacent quand il fait chaud ou clair --
    deux constantes dans un fichier ne sauraient pas le faire.

    La temperature y figure comme les autres, bien qu'aucun actionneur
    n'agisse sur elle : le reseau a appris a la JUGER, donc son seuil se
    lit au meme titre. C'est la difference entre un reseau qui commande
    et un reseau qui apprecie une situation.
    """
    p, meta, version = modele_courant()
    if p is None:
        return {"entraine": False}

    # Le contexte du balayage, ce sont les conditions du moment : c'est ce
    # qui rend les seuils mobiles plutot que figes.
    contexte = {capteur: valeur for capteur, valeur, _, _ in interroger(DERNIERES)}
    maintenant = datetime.now()
    contexte["heure"] = maintenant.hour + maintenant.minute / 60
    try:
        with base() as conn:
            contexte["eclairement_jour"] = eclairement.heures_du_jour(conn)
    except HTTPException:
        contexte["eclairement_jour"] = 0.0

    b = np.array(meta["bornes"])
    return {
        "entraine": True,
        "version": version,
        "architecture": meta["architecture"],
        "parametres": int(sum(np.asarray(v).size for v in p.values())),
        "grandeurs": meta["grandeurs"],
        "exactitude_test": meta["metriques"]["exactitude_test"],
        "exactitude_complete": meta["metriques"].get("exactitude_complete"),
        "seuils": seuils.frontieres(p, b, contexte),
        "contexte": {cle: round(float(v), 2) for cle, v in contexte.items()},
        "cible_lumiere_h": donnees.CIBLE_LUMIERE_H,
    }


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


def compte_ouvert(jeton: str | None) -> str | None:
    """L'identifiant derriere un cookie de session, ou None.

    Une seule porte d'entree : une verification ecrite deux fois est une
    verification qu'on oubliera de corriger une fois."""
    with base() as conn:
        return auth.compte_de(conn, jeton)


@app.get("/api/moi")
def moi(botanik_session: str | None = Cookie(default=None)):
    """Qui est connecte. Le frontend s'en sert pour decider s'il affiche
    le pilotage -- la verification reelle se fait a chaque commande."""
    return {"identifiant": compte_ouvert(botanik_session)}


@app.get("/api/actionneurs")
def actionneurs():
    """Les actionneurs actifs, chacun avec l'etat qu'il a lui-meme annonce.

    `valeur` a None signifie que l'actionneur ne s'est pas manifeste --
    service arrete, ou broker injoignable. Le dashboard doit pouvoir
    montrer cette difference : ne pas savoir n'est pas la meme chose
    qu'etre a l'arret.

    `verrou_s` dit combien de temps le modele s'abstient encore apres
    une reprise en main. Il est calcule ici et dans le cerveau par le
    MEME module, a partir du meme journal : l'ecran ne peut donc pas
    annoncer un verrou que le modele ignorerait. Le dashboard ne
    l'affiche pas encore -- c'est la seule information de cette reponse
    qui attend son emplacement.
    """
    connus = bus.etats()
    try:
        with base() as conn:
            fins = verrous.actifs(conn)
    except HTTPException:
        fins = {}

    actifs = registre.actionneurs_actifs()
    resolus = registre.resoudre(actifs, SORTIES)

    return [
        {
            "id": a["id"],
            "libelle": a["libelle"],
            "detail": a["detail"],
            # Meme distinction que pour les capteurs : un relais qui
            # n'est pas encore cable accepte les ordres sans rien faire.
            "simule": resolus.get(a["id"], {}).get("source") == "simule",
            "valeur": connus.get(a["id"], {}).get("valeur"),
            "ts": connus.get(a["id"], {}).get("ts"),
            # Secondes pendant lesquelles le modele s'abstient, apres
            # une reprise en main. Zero : il commande a nouveau.
            "verrou_s": verrous.restant(fins.get(a["id"])),
        }
        for a in actifs
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

    L'API ne fait qu'emettre : c'est le collecteur qui consigne, en
    ecoutant le topic. Ainsi une commande du modele, qui ne passe jamais
    par ici, se retrouve journalisee exactement comme une commande
    manuelle -- et `commandes` reste le journal de ce qui a REELLEMENT
    transite, non de ce qu'on a souhaite.
    """
    identifiant = compte_ouvert(botanik_session)
    if not identifiant:
        raise HTTPException(401, "connexion requise")

    topic = f"{TOPIC_COMMANDES}/{corps.actionneur}"
    if not bus.publier(topic, {"valeur": corps.valeur, "source": "manuel"}):
        raise HTTPException(503, "broker MQTT injoignable")
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
