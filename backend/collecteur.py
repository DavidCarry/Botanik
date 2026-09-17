"""Ecoute MQTT et archive en base.

Seul composant a ecrire dans `mesures` et `commandes`. Il journalise donc
TOUTES les commandes, d'ou qu'elles viennent -- le doigt de l'utilisateur
comme le modele -- puisqu'elles transitent toutes par le meme topic. Les
consigner ici plutot que dans l'API garantit qu'aucun emetteur ne peut
agir sans laisser de trace.

Un message malforme est ignore avec un avertissement : le collecteur ne
doit jamais s'arreter a cause d'un capteur qui deraille.
"""

import json
import shutil
from datetime import datetime, timedelta, timezone

import psycopg

import bdd
import schema
import service
from config import (
    ARCHIVAGE_S, ESPACE_MINIMAL_GO, TOPIC_ALERTES, TOPIC_COMMANDES,
    TOPIC_MESURES,
)

INSERTION = (
    "INSERT INTO mesures (ts, capteur, valeur, unite) VALUES (%s, %s, %s, %s)"
)

JOURNAL = (
    "INSERT INTO commandes (ts, actionneur, valeur, source) "
    "VALUES (%s, %s, %s, %s)"
)

# La colonne porte une contrainte : une source inconnue ferait echouer
# l'insertion. On la verifie ici pour signaler l'emetteur fautif plutot
# que de laisser remonter une erreur SQL opaque.
#
# Deux sources, et deux seulement : un clic, ou une regle de
# l'utilisateur. « ia » et « securite » sont partis avec les regles
# ecrites en dur -- plus personne ne les emet.
SOURCES = {"manuel", "regle"}

# Derniere mesure REELLEMENT ecrite pour chaque capteur.
#
# Les mesures arrivent deux fois par seconde, pour l'ecran ; on n'en
# garde qu'une toutes les `ARCHIVAGE_S`. Les courbes n'ont pas besoin de
# plus, et ecrire six cents fois par minute remplirait la carte pour rien.
#
# Seules les MESURES sont espacees. Les commandes et les alertes passent
# toutes, sans exception : ce sont des evenements, pas un echantillonnage,
# et en perdre un rendrait le journal faux.
_dernier_archivage: dict[str, datetime] = {}


def _a_archiver(capteur: str, ts: datetime) -> bool:
    """Vrai si assez de temps s'est ecoule depuis la derniere ecriture.

    Un capteur inconnu est toujours ecrit : au demarrage, chaque courbe
    gagne ainsi un point tout de suite au lieu d'attendre cinq minutes.
    """
    precedent = _dernier_archivage.get(capteur)
    if precedent is not None and ts - precedent < timedelta(seconds=ARCHIVAGE_S):
        return False
    _dernier_archivage[capteur] = ts
    return True


# Nombre de lignes effacees d'un coup quand la place vient a manquer.
# Assez pour que la boucle avance, assez peu pour ne pas bloquer la table
# pendant qu'une mesure cherche a s'inserer.
LOT_PURGE = 50_000

# Le disque ne se remplit pas en une seconde : le verifier toutes les
# cinq minutes suffit, et ne coute rien.
VERIFICATION_ESPACE_S = 300

PLUS_ANCIENNES = (
    "DELETE FROM mesures WHERE ctid IN "
    "(SELECT ctid FROM mesures ORDER BY ts LIMIT %s)"
)


def _espace_libre_go() -> float:
    return shutil.disk_usage("/").free / 1e9


def surveiller_espace(conn) -> None:
    """Efface les mesures les plus anciennes quand le disque se remplit.

    Le raisonnement : une serre qui ne peut plus enregistrer ce qui se
    passe MAINTENANT est en panne, alors qu'une serre qui a oublie le
    mois dernier fonctionne encore. En cas de conflit, le present gagne.

    On vide par lots plutot que d'un bloc, et on repasse le balai
    derriere : un simple VACUUM ne rend pas la place au systeme, mais il
    rend les pages reutilisables par les insertions suivantes -- ce qui
    est exactement ce qu'on cherche. Un VACUUM FULL, lui, reecrirait la
    table entiere, et reclamerait donc la place qui vient justement de
    manquer.
    """
    libre = _espace_libre_go()
    if libre >= ESPACE_MINIMAL_GO:
        return

    print(f"ALERTE STOCKAGE : {libre:.2f} Go libres, sous le seuil de "
          f"{ESPACE_MINIMAL_GO} Go -- purge des mesures les plus anciennes",
          flush=True)
    try:
        with conn.cursor() as cur:
            cur.execute(PLUS_ANCIENNES, (LOT_PURGE,))
            efacees = cur.rowcount
            cur.execute("VACUUM mesures")
        print(f"  {efacees} mesures effacees, {_espace_libre_go():.2f} Go libres",
              flush=True)
        if efacees == 0:
            print("  plus rien a effacer : le disque se remplit AILLEURS "
                  "que dans les mesures", flush=True)
    except psycopg.Error as e:
        print(f"  purge impossible : {e}", flush=True)
        conn.rollback()

# Une alerte est un episode, pas un instant : on ouvre une ligne quand le
# probleme apparait, on la ferme quand il cesse. `fin IS NULL` designe
# donc ce qui est en cours, sans etat entretenu ailleurs.
FERMER = "UPDATE alertes SET fin = %s WHERE grandeur = %s AND fin IS NULL"

# N'ouvre que s'il n'y a pas deja un episode en cours du meme cote. Le
# message d'alerte etant retenu, un service qui redemarre le recoit a
# nouveau : sans cette garde, chaque redemarrage creerait un doublon.
OUVRIR = """
    INSERT INTO alertes (grandeur, cote, debut)
    SELECT %s, %s, %s
    WHERE NOT EXISTS (
        SELECT 1 FROM alertes WHERE grandeur = %s AND cote = %s AND fin IS NULL
    )
"""


def _horodatage(brut):
    """Prefere l'instant de la mesure a celui de l'insertion."""
    if not brut:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(brut)
    except ValueError:
        return datetime.now(timezone.utc)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"Connexion MQTT refusee : {reason_code}", flush=True)
        return
    client.subscribe(f"{TOPIC_MESURES}/#")
    client.subscribe(f"{TOPIC_COMMANDES}/#", qos=1)
    client.subscribe(f"{TOPIC_ALERTES}/#", qos=1)
    print(f"Abonne aux mesures, aux commandes et aux alertes", flush=True)


def _alerte(conn, grandeur, data):
    """Ouvre ou ferme l'episode en cours pour cette grandeur."""
    instant = _horodatage(data.get("ts"))
    cote = data.get("cote")
    with conn.cursor() as cur:
        if cote not in ("bas", "haut"):
            cur.execute(FERMER, (instant, grandeur))
            return f"alerte levee : {grandeur}" if cur.rowcount else None
        # Un basculement direct d'un cote a l'autre ferme le precedent.
        cur.execute(
            "UPDATE alertes SET fin = %s "
            "WHERE grandeur = %s AND cote <> %s AND fin IS NULL",
            (instant, grandeur, cote),
        )
        cur.execute(OUVRIR, (grandeur, cote, instant, grandeur, cote))
        return f"alerte ouverte : {grandeur} {cote}" if cur.rowcount else None


def on_message(client, conn, msg):
    identifiant = msg.topic.rsplit("/", 1)[-1]
    try:
        data = json.loads(msg.payload)
    except json.JSONDecodeError as e:
        print(f"Message ignore sur {msg.topic} : {e}", flush=True)
        return

    if msg.topic.startswith(TOPIC_ALERTES):
        try:
            trace = _alerte(conn, identifiant, data)
        except psycopg.Error as e:
            print(f"Echec d'ecriture d'alerte pour {identifiant} : {e}", flush=True)
            conn.rollback()
            return
        if trace:
            print(trace, flush=True)
        return

    try:
        valeur = float(data["valeur"])
    except (KeyError, TypeError, ValueError) as e:
        print(f"Message ignore sur {msg.topic} : {e}", flush=True)
        return

    commande = msg.topic.startswith(TOPIC_COMMANDES)
    if commande:
        source = data.get("source", "manuel")
        if source not in SOURCES:
            print(f"Commande ignoree sur {msg.topic} : source '{source}' inconnue",
                  flush=True)
            return
        # Une salve fait clignoter l'avertisseur toutes les secondes.
        # L'ordre est deja au journal ; ses battements n'y ajoutent rien
        # et noieraient tout le reste.
        if not data.get("journal", True):
            return
        requete = (JOURNAL, (_horodatage(data.get("ts")), identifiant, valeur, source))
        trace = f"commande {identifiant} = {valeur} ({source})"
    else:
        ts = _horodatage(data.get("ts"))
        if not _a_archiver(identifiant, ts):
            return          # diffusee a l'ecran, mais pas archivee
        requete = (INSERTION, (ts, identifiant, valeur, data.get("unite")))
        trace = f"{identifiant} = {valeur} {data.get('unite', '')}"

    try:
        with conn.cursor() as cur:
            cur.execute(*requete)
        print(trace, flush=True)
    except psycopg.Error as e:
        print(f"Echec d'insertion pour {identifiant} : {e}", flush=True)
        conn.rollback()


def main():
    conn = bdd.connexion()
    # Idempotent : la table des alertes peut ne pas exister si l'API n'a
    # jamais demarre sur cette base.
    schema.preparer(conn)
    print("Connecte a la base", flush=True)

    print(f"Archivage : un point toutes les {ARCHIVAGE_S:.0f}s par capteur, "
          f"garde-fou a {ESPACE_MINIMAL_GO} Go", flush=True)

    # L'essentiel se joue dans on_message ; le battement ne sert qu'a
    # surveiller la place restante.
    service.executer(
        "Collecteur", periode=VERIFICATION_ESPACE_S, userdata=conn,
        travail=lambda _client: surveiller_espace(conn),
        on_connect=on_connect, on_message=on_message,
    )
    conn.close()


if __name__ == "__main__":
    main()
