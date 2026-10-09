"""Serveur de l'application Botanik.

Expose l'etat des capteurs et sert le frontend compile.

ATTENTION a l'ordre des declarations : le montage des fichiers statiques se
fait sur "/" et intercepte donc tout. Les routes /api doivent imperativement
etre declarees AVANT, sinon elles ne sont jamais atteintes.
"""

import asyncio
import base64
import json
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from fastapi import (Cookie, Depends, FastAPI, Header, HTTPException,
                     Response)
from fastapi.middleware.cors import CORSMiddleware
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
import empreintes
import poids as magasin
import registre
import regles
import regles_visages
import schema
import seuils
import systeme
import verrous
from config import (
    ARCHIVAGE_S, CAMERA_FICHIER, CAMERA_FRAICHEUR_S, TOPIC_COMMANDES,
    TOPIC_REGLES,
)
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

# L'application Android sert ses pages depuis l'APK : elles ne viennent
# donc plus de la meme origine que l'API, et le navigateur refuse la
# requete sans cette autorisation explicite. Le navigateur de bureau, lui,
# charge tout depuis ce serveur et n'est pas concerne.
#
# L'origine est « http » et non « https » : une page servie en https ne
# peut pas appeler une API en clair, et la serre n'a pas de certificat.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "capacitor://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def jeton_session(
    botanik_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> str | None:
    """Le jeton de session, d'ou qu'il vienne.

    Le navigateur envoie un cookie, et c'est tres bien : marque httponly,
    il reste hors de portee du JavaScript de la page.

    L'application Android, elle, affiche des pages embarquees dans l'APK.
    Elles sont donc sur une autre origine que l'API, et un cookie ne
    franchit cette frontiere qu'en HTTPS -- que la serre n'a pas. Elle
    presente donc le MEME jeton dans un en-tete, qui passe partout.
    """
    if botanik_session:
        return botanik_session
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def plages_affichees() -> dict[str, dict | None]:
    """La plage a montrer pour chaque grandeur, d'apres les regles.

    Rien n'est invente : une grandeur sans regle n'a pas de plage, et
    l'ecran ne trace alors aucune ligne. Afficher la plage du registre
    par defaut, comme on le faisait, laissait croire a une consigne que
    personne n'avait donnee.
    """
    with base() as conn:
        posees = regles.lire(conn)
    if not posees:
        return {}

    appris = {}
    p, meta, _ = modele_courant()
    if p is not None and any(
            b.mode == "ia"
            for r in posees.values() for b in (r.bas, r.haut)):
        contexte = {c: v for c, v, _, _ in interroger(DERNIERES)}
        maintenant = datetime.now()
        contexte["heure"] = maintenant.hour + maintenant.minute / 60
        try:
            with base() as conn:
                contexte["eclairement_jour"] = eclairement.heures_du_jour(conn)
        except HTTPException:
            contexte["eclairement_jour"] = 0.0
        appris = seuils.frontieres(p, np.array(meta["bornes"]), contexte)

    return {g: decision.plage(r, appris.get(g)) for g, r in posees.items()}


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
    plages = plages_affichees()

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
            "echelle": c["echelle"],
            # La plage voulue par l'utilisateur, ou None s'il n'en a
            # defini aucune. Une borne a None : ce cote est infini.
            "plage": plages.get(c["id"]),
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

# Et dix secondes quand il n'y en a pas : le temps d'un entrainement.
ATTENTE_MODELE_S = 10
_modele: dict = {"relu": 0.0}


def modele_courant():
    """Poids et metadonnees du modele, ou None si aucun n'est entraine."""
    # L'ABSENCE de modele ne se met pas en cache aussi longtemps que sa
    # presence : un modele entraine ne disparait pas, alors qu'un modele
    # manquant est un etat transitoire -- on vient de lancer
    # l'entrainement, il arrivera dans la minute. Garder « aucun modele »
    # cinq minutes laissait le tableau de bord annoncer une serre sans
    # cerveau bien apres qu'elle en ait retrouve un.
    age = time.time() - _modele["relu"]
    connu = _modele.get("poids") is not None
    if "poids" in _modele and age < (RELECTURE_MODELE_S if connu else ATTENTE_MODELE_S):
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


# Formulations sans accord : « Temperature trop haut » etait faux, et
# accorder demanderait de connaitre le genre de chaque libelle. Dire ou
# se situe la mesure par rapport a la borne evite le probleme et dit
# exactement la meme chose.
COTES = {"bas": "sous la borne", "haut": "au-dessus de la borne"}


def noms_alertes() -> dict:
    """Comment nommer chaque alerte, et laquelle demande quelqu'un.

    Plus de table ecrite en dur : le libelle vient du registre -- c'est
    le capteur qui se nomme -- et la gravite se deduit de la regle.
    Si l'utilisateur a prevu une action pour ce cote, la serre s'en
    occupe ; s'il n'en a prevu aucune, personne d'autre qu'un humain ne
    peut y remedier, et l'alerte le dit.
    """
    capteurs = {c["id"]: c["libelle"] for c in registre.capteurs_actifs()}
    try:
        with base() as conn:
            posees = regles.lire(conn)
    except HTTPException:
        posees = {}

    noms = {}
    for grandeur, libelle in capteurs.items():
        regle = posees.get(grandeur)
        for cote, mention in COTES.items():
            action = getattr(regle, f"action_{cote}", None) if regle else None
            noms[(grandeur, cote)] = {
                "libelle": f"{libelle} {mention}",
                "humaine": action is None or action.genre == "aucun",
            }
    return noms


def _nom_alerte(noms: dict, grandeur: str, cote: str) -> dict:
    return noms.get((grandeur, cote),
                    {"libelle": f"{grandeur} {cote}", "humaine": True})


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
    noms = noms_alertes()
    return [
        {"grandeur": grandeur, "cote": cote, "depuis": debut.isoformat(),
         **_nom_alerte(noms, grandeur, cote)}
        for grandeur, cote, debut in lignes
    ]


@app.get("/api/evenements")
def evenements(limite: int = 40):
    """Journal melant les commandes et les alertes, du plus recent au plus
    ancien.

    Les deux dans le meme flux, parce qu'ils se lisent ensemble : « sol
    trop sec detecte », puis « arrosage active », puis « sol trop sec
    leve ». Separes en deux listes, la causalite disparaitrait.

    `source` dit qui a decide d'une commande : un clic de l'utilisateur,
    ou une des regles qu'il a posees.
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
    noms = noms_alertes()
    evenements_alertes = [
        {"genre": "alerte", "ts": ts.isoformat(), "sujet": grandeur,
         "cote": cote, "ouverture": ouverture,
         **_nom_alerte(noms, grandeur, cote)}
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


class BorneRecue(BaseModel):
    mode: str
    valeur: float | None = None
    action: dict | None = None


class RegleRecue(BaseModel):
    bas: BorneRecue
    haut: BorneRecue


def _verifier_action(brut: dict | None) -> decision.Action | None:
    """Valide une action avant de l'enregistrer.

    Le cerveau tourne sans surveillance : une action qui designe un
    actionneur retire du registre le ferait publier dans le vide pour
    toujours. On refuse ici, ou l'utilisateur peut encore l'apprendre.
    """
    if not brut or brut.get("genre") in (None, "aucun"):
        return None

    genre = brut.get("genre")
    connus = {a["id"] for a in registre.actionneurs_actifs()}

    if genre == "actionneur":
        if brut.get("cible") not in connus:
            raise HTTPException(400, f"actionneur inconnu : {brut.get('cible')}")
        return decision.Action("actionneur", brut["cible"],
                               1.0 if brut.get("valeur") else 0.0)

    if genre == "ecran":
        if brut.get("cible", "ecran") not in connus:
            raise HTTPException(400, "aucun afficheur disponible")
        texte = (brut.get("texte") or "").strip()
        if not texte:
            raise HTTPException(400, "texte d'affichage vide")
        return decision.Action("ecran", brut.get("cible", "ecran"),
                               texte=texte[:TEXTE_MAXIMAL])

    raise HTTPException(400, f"genre d'action inconnu : {genre}")


@app.get("/api/regles")
def lire_regles():
    """Les regles en place, et de quoi les editer.

    Renvoie aussi les seuils que le reseau vient d'apprendre et les
    actionneurs disponibles : l'ecran ne doit pas avoir a les deviner,
    ni proposer un actionneur qui n'existe plus.
    """
    p, meta, _ = modele_courant()
    appris = {}
    if p is not None:
        contexte = {c: v for c, v, _, _ in interroger(DERNIERES)}
        maintenant = datetime.now()
        contexte["heure"] = maintenant.hour + maintenant.minute / 60
        try:
            with base() as conn:
                contexte["eclairement_jour"] = eclairement.heures_du_jour(conn)
        except HTTPException:
            contexte["eclairement_jour"] = 0.0
        appris = seuils.frontieres(p, np.array(meta["bornes"]), contexte)

    capteurs = {c["id"]: c for c in registre.capteurs_actifs()}
    with base() as conn:
        posees = {r["grandeur"]: r for r in regles.brutes(conn)}
        lumiere_utile = eclairement.reglage(conn)

    # Toutes les grandeurs jugees, pas seulement celles qui sortent d'un
    # capteur : la lumiere recue est un cumul, et c'est pourtant elle qui
    # porte le budget quotidien -- la filtrer la rendait inreglable.
    # Capteur ou non, une grandeur se decrit par les memes trois champs.
    return {
        "grandeurs": [
            {
                "id": g,
                "libelle": d["libelle"],
                "unite": d.get("unite", ""),
                "echelle": d.get("echelle"),
                "seuil_ia": appris.get(g),
                "regle": posees.get(g),
            }
            for g in decision.GRANDEURS
            # Une grandeur qu'on ne sait pas nommer n'est pas proposee :
            # un capteur desactive disparait des reglages, comme avant.
            if (d := capteurs.get(g) or registre.HORS_CAPTEUR.get(g))
        ],
        "actionneurs": [
            {"id": a["id"], "libelle": a["libelle"]}
            for a in registre.actionneurs_actifs()
        ],
        # A partir de quelle clarte la lumiere compte dans le cumul. Pas
        # une borne de regle : ce reglage ne declenche rien, il dit ce
        # que « douze heures de lumiere » veut dire. Meme forme qu'une
        # borne malgre tout -- un mode, une valeur -- parce qu'il se
        # regle de la meme facon.
        "lumiere_utile": lumiere_utile,
    }


@app.put("/api/regles/{grandeur}")
def poser_regle(grandeur: str, corps: RegleRecue,
                botanik_session: str | None = Depends(jeton_session)):
    """Pose ou remplace la regle d'une grandeur."""
    if not compte_ouvert(botanik_session):
        raise HTTPException(401, "connexion requise")
    if grandeur not in decision.GRANDEURS:
        raise HTTPException(400, f"grandeur inconnue : {grandeur}")

    regle = decision.Regle(
        bas=decision.Borne(corps.bas.mode, corps.bas.valeur),
        haut=decision.Borne(corps.haut.mode, corps.haut.valeur),
        action_bas=_verifier_action(corps.bas.action),
        action_haut=_verifier_action(corps.haut.action),
    )
    try:
        with base() as conn:
            regles.enregistrer(conn, grandeur, regle)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    # Le cerveau relit aussitot plutot qu'a son prochain tour de garde,
    # et les ecrans ouverts voient la nouvelle plage sans attendre leur
    # propre relecture : une borne qu'on vient de poser doit apparaitre
    # sur la bulle tout de suite, sinon on doute de l'avoir enregistree.
    bus.publier(TOPIC_REGLES, {"grandeur": grandeur})
    bus.diffuser({"genre": "plages", "plages": plages_affichees()})
    return {"ok": True}


@app.delete("/api/regles/{grandeur}")
def retirer_regle(grandeur: str,
                  botanik_session: str | None = Depends(jeton_session)):
    """Retire la regle d'une grandeur : la serre cesse de s'en occuper."""
    if not compte_ouvert(botanik_session):
        raise HTTPException(401, "connexion requise")
    with base() as conn:
        efface = regles.retirer(conn, grandeur)
    bus.publier(TOPIC_REGLES, {"grandeur": grandeur})
    bus.diffuser({"genre": "plages", "plages": plages_affichees()})
    return {"ok": efface}


class ClarteUtile(BaseModel):
    mode: str
    utile: float | None = None


@app.put("/api/eclairement")
def regler_eclairement(corps: ClarteUtile,
                       botanik_session: str | None = Depends(jeton_session)):
    """Pose la clarte a partir de laquelle la lumiere compte dans le cumul.

    Sa propre route, et non une troisieme borne de la regle
    `eclairement_jour` : ce n'est pas un seuil qui declenche, c'est la
    definition de ce qu'on compte. Il se REGLE comme une borne -- « ia »
    ou « manuel » -- mais il n'agit sur rien tout seul.
    """
    if not compte_ouvert(botanik_session):
        raise HTTPException(401, "connexion requise")

    # Borne sur l'echelle declaree du capteur, et non sur un 0-100 ecrit
    # ici : le jour ou la luminosite se mesurera en lux, cette route
    # suivra sans qu'on y pense.
    #
    # Verifiee des qu'un chiffre est donne, meme en mode « ia » ou il ne
    # sert pas : il est conserve pour le retour en manuel, et une valeur
    # hors echelle rangee en attendant ressortirait un jour.
    if corps.utile is not None:
        capteur = next((c for c in registre.capteurs_actifs()
                        if c["id"] == "luminosite"), None)
        if capteur is None:
            raise HTTPException(409, "aucun capteur de luminosite actif")
        echelle = capteur["echelle"]
        if not float(echelle["min"]) <= corps.utile <= float(echelle["max"]):
            raise HTTPException(400, "la clarté utile doit tenir entre "
                                     f"{echelle['min']} et {echelle['max']}")

    try:
        with base() as conn:
            eclairement.regler(conn, corps.mode, corps.utile)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    # Le cumul change de sens : le cerveau perime son contexte des qu'il
    # voit passer ce message et le relit au tour suivant, au lieu
    # d'attendre sa relecture periodique.
    bus.publier(TOPIC_REGLES, {"grandeur": "eclairement_jour"})
    return {"ok": True}


# ---------------------------------------------------------------
# Les visages : qui la serre connait, et ce qu'elle en fait
# ---------------------------------------------------------------

# Les deux sujets qui ne designent personne en particulier. Ils sont
# toujours proposes, meme quand la serre ne connait encore personne :
# « quelqu'un est la » ne demande aucune reference.
SUJETS_SPECIAUX = [
    {"id": decision.QUICONQUE, "libelle": "Quelqu’un",
     "detail": "n’importe qui, connu ou non"},
    {"id": decision.INCONNU, "libelle": "Un inconnu",
     "detail": "un visage qui ne correspond à aucune référence"},
]


class ActionVisageRecue(BaseModel):
    action: dict | None = None


@app.get("/api/visages")
def lire_visages():
    """Qui la serre sait nommer, et ce qu'elle en fait.

    Les personnes et les sujets speciaux sont rendus separement : seules
    les premieres peuvent etre oubliees, et l'ecran doit savoir sur
    lesquelles proposer une corbeille.
    """
    with base() as conn:
        personnes = empreintes.inventaire(conn)
        posees = regles_visages.brutes(conn)

    return {
        "speciaux": SUJETS_SPECIAUX,
        "personnes": [
            {"id": nom, "libelle": nom.capitalize(), "references": combien}
            for nom, combien in personnes
        ],
        "regles": posees,
        "actionneurs": [
            {"id": a["id"], "libelle": a["libelle"]}
            for a in registre.actionneurs_actifs()
        ],
    }


class VisageRecu(BaseModel):
    nom: str
    # La photo en base64, avec ou sans l'en-tete « data: » que met un
    # navigateur.
    #
    # Du JSON et non du multipart : `UploadFile` reclamerait
    # `python-multipart`, une dependance de plus a poser sur une Pi dont
    # l'installation des dependances est deja fragile. Et l'interface
    # reduit la photo avant de l'envoyer, donc le corps reste leger --
    # le base64 ne coute ses trente pour cent que sur quelques centaines
    # de kilo-octets.
    image: str


# Au-dela, on refuse sans meme decoder. Une reference n'a pas besoin de
# plus : le detecteur ramene de toute facon l'image a 640 pixels de
# large, et accepter n'importe quoi ouvrirait la porte a saturer la
# memoire de la Pi avec un seul appel.
VISAGE_OCTETS_MAX = 8 * 1024 * 1024

# Ce qu'un nom de personne peut contenir. Il sert de CLE a une regle de
# visage et s'affiche tel quel : on ecarte d'emblee ce qui romprait l'un
# ou l'autre. Une lettre pour commencer, trente-deux caracteres au plus.
NOM_VISAGE = re.compile(r"^[^\W\d_][\w .'’-]{0,31}$")


@app.post("/api/visages")
def apprendre_visage(corps: VisageRecu,
                     botanik_session: str | None = Depends(jeton_session)):
    """Apprend une personne a partir d'une photo.

    Ce qui est garde n'est PAS la photo mais son empreinte -- les 128
    nombres que le modele tire du visage. La photo est oubliee des que la
    reponse part, et la carte de la Pi ne porte donc jamais de galerie de
    portraits.

    Plusieurs photos d'une meme personne s'ajoutent les unes aux autres,
    de face puis de trois quarts : c'est la meilleure des ressemblances
    qui decidera. Reapprendre quelqu'un ne remplace donc rien, ca
    l'affine.

    Le service de reconnaissance relit les references toutes les dix
    secondes : la nouvelle personne est nommee devant la camera sans
    qu'on redemarre quoi que ce soit.
    """
    if not compte_ouvert(botanik_session):
        raise HTTPException(401, "connexion requise")

    nom = corps.nom.strip().lower()
    if not NOM_VISAGE.match(nom):
        raise HTTPException(400, "nom invalide : une lettre pour commencer, "
                                 "32 caractères au plus")
    if nom in decision.SUJETS_RESERVES:
        raise HTTPException(400, f"« {nom} » désigne déjà autre chose")

    brut = corps.image.split(",", 1)[-1]
    try:
        octets = base64.b64decode(brut, validate=True)
    except ValueError as e:
        raise HTTPException(400, "image illisible") from e
    if not octets:
        raise HTTPException(400, "image vide")
    if len(octets) > VISAGE_OCTETS_MAX:
        raise HTTPException(413, "image trop lourde")

    # Importe ICI, et non en tete de fichier : OpenCV et ses modeles
    # pesent des dizaines de mega-octets, et l'API ne s'en sert que
    # lorsqu'on apprend quelqu'un -- c'est-a-dire presque jamais. Les
    # charger au demarrage les ferait porter a l'API pour toujours.
    import visages

    if visages.cv2 is None:
        raise HTTPException(503, "OpenCV absent sur la serre")
    # Une detection n'a pas besoin de tous les coeurs, et l'API en
    # partage quatre avec six autres services.
    visages.cv2.setNumThreads(1)

    image = visages.cv2.imdecode(np.frombuffer(octets, dtype=np.uint8),
                                 visages.cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400, "image illisible — JPEG ou PNG attendu")

    try:
        with base() as conn:
            vu = visages.apprendre(visages.regard_de_reference(), conn, nom,
                                   image, "interface")
            vu["references"] = next(
                (c for n, c in empreintes.inventaire(conn) if n == nom), 1)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    return {"ok": True, **vu}


def _sujet_connu(conn, sujet: str) -> bool:
    if sujet in (decision.QUICONQUE, decision.INCONNU):
        return True
    return any(nom == sujet for nom, _ in empreintes.inventaire(conn))


@app.put("/api/visages/regles/{sujet}")
def poser_regle_visage(sujet: str, corps: ActionVisageRecue,
                       botanik_session: str | None = Depends(jeton_session)):
    """Pose ou remplace ce que la serre fait en voyant ce sujet."""
    if not compte_ouvert(botanik_session):
        raise HTTPException(401, "connexion requise")

    action = _verifier_action(corps.action)
    if action is None:
        raise HTTPException(400, "une règle de visage demande une action")

    try:
        with base() as conn:
            if not _sujet_connu(conn, sujet):
                raise HTTPException(400, f"sujet inconnu : {sujet}")
            regles_visages.enregistrer(conn, sujet, action)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    bus.publier(TOPIC_REGLES, {"visage": sujet})
    return {"ok": True}


@app.delete("/api/visages/regles/{sujet}")
def retirer_regle_visage(sujet: str,
                         botanik_session: str | None = Depends(jeton_session)):
    """La serre continue de reconnaitre ce sujet, sans plus rien en faire."""
    if not compte_ouvert(botanik_session):
        raise HTTPException(401, "connexion requise")
    with base() as conn:
        efface = regles_visages.retirer(conn, sujet)
    bus.publier(TOPIC_REGLES, {"visage": sujet})
    return {"ok": efface}


@app.delete("/api/visages/{nom}")
def oublier_visage(nom: str,
                   botanik_session: str | None = Depends(jeton_session)):
    """Oublie une personne : ses empreintes ET son declencheur.

    Les deux, et pas seulement les empreintes. Une regle laissee derriere
    designerait un sujet que la serre ne peut plus reconnaitre -- donc une
    ligne morte, invisible a l'ecran puisque la page ne liste que les
    personnes connues. Elle RESSUSCITERAIT au premier reapprentissage du
    meme nom, avec une action que plus personne n'avait en tete.

    C'est sans retour : on ne garde pas les photos, seulement les 128
    nombres qu'on en tire, et il faudra reprendre une photo pour
    reapprendre quelqu'un. L'ecran demande confirmation avant d'appeler.

    Declaree APRES les routes `/api/visages/regles/...`, sinon son
    `{nom}` les avalerait.
    """
    if not compte_ouvert(botanik_session):
        raise HTTPException(401, "connexion requise")

    vise = nom.strip().lower()
    if vise in decision.SUJETS_RESERVES or vise == "regles":
        raise HTTPException(400, f"« {vise} » n'est pas une personne")

    with base() as conn:
        efface = empreintes.retirer(conn, vise)
        if not efface:
            raise HTTPException(404, f"« {vise} » n'est pas connu de la serre")
        regles_visages.retirer(conn, vise)

    # Le service de reconnaissance relit ses references toutes les dix
    # secondes ; le cerveau, lui, doit perimer ses regles tout de suite.
    bus.publier(TOPIC_REGLES, {"visage": vise})
    return {"ok": True, "references": efface}


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
        # Age de la derniere prise de vue. None : aucune camera ne
        # produit d'image, l'ecran retombe sur la photo du chassis.
        "camera_s": age_de_la_vue(),
    }


def age_de_la_vue() -> float | None:
    """Secondes depuis la derniere prise de vue, ou None s'il n'y en a pas."""
    try:
        return round(time.time() - Path(CAMERA_FICHIER).stat().st_mtime, 1)
    except OSError:
        return None


@app.get("/api/camera.jpg")
def vue_camera():
    """La derniere image prise par la camera de la serre.

    Une image fixe renouvelee, pas un flux : le navigateur la redemande
    quand il veut. `no-store` est indispensable -- sans lui, le
    navigateur servirait indefiniment la premiere.

    Le fichier est remplace de facon atomique par le service de prise de
    vue : on ne sert donc jamais une image a moitie ecrite.
    """
    age = age_de_la_vue()
    if age is None:
        raise HTTPException(404, "aucune prise de vue")
    if age > CAMERA_FRAICHEUR_S:
        raise HTTPException(503, f"derniere vue il y a {age} s")
    return FileResponse(CAMERA_FICHIER, media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})


# Separateur des trames du flux video, et pause entre deux examens du
# fichier.
#
# Dix millisecondes : le guet doit etre PLUS RAPIDE que la prise de vue,
# sinon il en manque une sur deux et la cadence s'effondre de moitie.
# A trente images par seconde une vue arrive toutes les 33 ms ; guetter
# au meme rythme aurait suffi a tout desynchroniser.
TRAME = b"--trame"
GUET_S = 0.01


@app.get("/api/camera.mjpg")
async def flux_camera():
    """Les vues de la camera, en flux continu.

    Une image redemandee une par une plafonne a la cadence des
    allers-retours HTTP, et chaque requete recommence tout : connexion,
    en-tetes, decodage. A dix images par seconde cela se voyait -- ca
    saccadait.

    Ici le navigateur ouvre UNE connexion et recoit les images a mesure
    qu'elles arrivent. C'est le vieux `multipart/x-mixed-replace`, que
    toutes les camera de surveillance utilisent : une balise `img`
    l'affiche sans une ligne de JavaScript, et sans clignoter.

    On ne renvoie une trame que lorsque le fichier a CHANGE : sinon on
    enverrait trente fois la meme image par seconde.
    """
    chemin = Path(CAMERA_FICHIER)

    async def trames():
        derniere = 0.0
        while True:
            try:
                instant = chemin.stat().st_mtime
            except OSError:
                # Pas de camera : on attend qu'elle revienne plutot que
                # de fermer le flux, que le navigateur devrait rouvrir.
                await asyncio.sleep(1.0)
                continue

            if instant != derniere:
                derniere = instant
                try:
                    image = chemin.read_bytes()
                except OSError:
                    continue
                # Les separateurs de trames sont des CRLF, comme
                # l exige le format multipart.
                entete = (b"\r\nContent-Type: image/jpeg\r\n"
                          + b"Content-Length: " + str(len(image)).encode()
                          + b"\r\n\r\n")
                yield TRAME + entete + image + b"\r\n"
            await asyncio.sleep(GUET_S)

    return StreamingResponse(
        trames(),
        media_type="multipart/x-mixed-replace; boundary=" + TRAME[2:].decode(),
        headers={"Cache-Control": "no-store"},
    )


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
    # Le jeton est rendu DANS LA REPONSE en plus du cookie : l'application
    # Android ne peut pas s'appuyer sur le cookie, elle garde celui-ci et
    # le represente en en-tete. Le navigateur, lui, l'ignore.
    return {"identifiant": corps.identifiant, "jeton": jeton}


@app.post("/api/deconnexion")
def deconnexion(reponse: Response, botanik_session: str | None = Depends(jeton_session)):
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
def moi(botanik_session: str | None = Depends(jeton_session)):
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
            # Meme distinction que pour les capteurs, et meme priorite :
            # ce que l'actionneur a REELLEMENT annonce fait foi, le
            # registre ne sert que tant qu'il n'a rien dit.
            "simule": connus.get(a["id"], {}).get(
                "simule", resolus.get(a["id"], {}).get("source") == "simule"),
            "valeur": connus.get(a["id"], {}).get("valeur"),
            "ts": connus.get(a["id"], {}).get("ts"),
            # Un afficheur porte en plus ce qu'on lui a demande de
            # montrer, et les deux lignes reellement ecrites dessus.
            "contenu": connus.get(a["id"], {}).get("contenu"),
            "lignes": connus.get(a["id"], {}).get("lignes"),
            # Secondes pendant lesquelles le modele s'abstient, apres
            # une reprise en main. Zero : il commande a nouveau.
            "verrou_s": verrous.restant(fins.get(a["id"])),
        }
        for a in actifs
    ]


# Longueur utile de l'afficheur : deux lignes de seize caracteres.
TEXTE_MAXIMAL = 32


class Contenu(BaseModel):
    """Ce qu'un afficheur doit montrer.

    Une INTENTION, pas un texte fige : « la temperature » suit la mesure,
    la ou « 23.6 C » resterait affiche apres coup.

    Plusieurs capteurs sont acceptes : ils defilent alors a l'ecran,
    cinq secondes chacun.
    """
    mode: str
    capteur: str | None = None
    capteurs: list[str] | None = None
    texte: str | None = None


class Commande(BaseModel):
    actionneur: str
    valeur: float
    contenu: Contenu | None = None


def verifier_contenu(contenu: Contenu) -> dict:
    """Valide ce qu'on demande d'afficher, avant de l'emettre.

    Le service qui pilote l'ecran tourne sans surveillance : lui envoyer
    un capteur qui n'existe pas le ferait afficher un identifiant brut
    pour toujours. On refuse ici, ou le client peut encore l'apprendre.
    """
    if contenu.mode == "texte":
        texte = (contenu.texte or "").strip()
        if not texte:
            raise HTTPException(400, "texte vide")
        return {"mode": "texte", "texte": texte[:TEXTE_MAXIMAL]}

    if contenu.mode == "mesure":
        connus = {c["id"] for c in registre.capteurs_actifs()}
        demandes = contenu.capteurs or (
            [contenu.capteur] if contenu.capteur else [])
        # On garde l'ordre demande, sans doublon : c'est celui du
        # defilement, et l'utilisateur l'a choisi.
        choisis = list(dict.fromkeys(demandes))
        if not choisis:
            raise HTTPException(400, "aucun capteur choisi")
        for c in choisis:
            if c not in connus:
                raise HTTPException(400, f"capteur inconnu : {c}")
        return {"mode": "mesure", "capteurs": choisis}

    raise HTTPException(400, f"mode d'affichage inconnu : {contenu.mode}")


@app.post("/api/commandes")
def commander(
    corps: Commande, botanik_session: str | None = Depends(jeton_session),
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

    charge = {"valeur": corps.valeur, "source": "manuel"}
    if corps.contenu is not None:
        charge["contenu"] = verifier_contenu(corps.contenu)

    topic = f"{TOPIC_COMMANDES}/{corps.actionneur}"
    if not bus.publier(topic, charge):
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

        # `index.html` ne se met JAMAIS en cache.
        #
        # Il ne pese rien, et c'est lui qui nomme les fichiers de
        # l'application -- dont le nom porte une empreinte qui change a
        # chaque compilation. Servi sans en-tete, le navigateur lui
        # appliquait sa propre heuristique et pouvait continuer a charger
        # la version precedente apres un deploiement : l'ecran semblait
        # alors ignorer des corrections pourtant en place, et on cherchait
        # le defaut dans le serveur.
        #
        # Les fichiers d'assets, eux, se mettent en cache sans risque :
        # leur nom change des que leur contenu change.
        return FileResponse(DIST / "index.html",
                            headers={"Cache-Control": "no-store"})
else:
    # Pas bloquant : en developpement le front est servi par Vite sur :5173,
    # et l'API doit pouvoir tourner seule.
    print(f"Frontend non compile ({DIST}) -- seules les routes /api repondent")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
