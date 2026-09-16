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
from datetime import datetime, timezone

import psycopg

import service
import schema
from config import DB_URL, TOPIC_ALERTES, TOPIC_COMMANDES, TOPIC_MESURES

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
SOURCES = {"manuel", "ia", "securite"}

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
        requete = (JOURNAL, (_horodatage(data.get("ts")), identifiant, valeur, source))
        trace = f"commande {identifiant} = {valeur} ({source})"
    else:
        requete = (INSERTION, (_horodatage(data.get("ts")), identifiant, valeur,
                               data.get("unite")))
        trace = f"{identifiant} = {valeur} {data.get('unite', '')}"

    try:
        with conn.cursor() as cur:
            cur.execute(*requete)
        print(trace, flush=True)
    except psycopg.Error as e:
        print(f"Echec d'insertion pour {identifiant} : {e}", flush=True)
        conn.rollback()


def main():
    conn = psycopg.connect(DB_URL, autocommit=True)
    # Idempotent : la table des alertes peut ne pas exister si l'API n'a
    # jamais demarre sur cette base.
    schema.preparer(conn)
    print("Connecte a la base", flush=True)

    # Rien a faire periodiquement : tout se joue dans on_message.
    service.executer(
        "Collecteur", periode=0.5, userdata=conn,
        on_connect=on_connect, on_message=on_message,
    )
    conn.close()


if __name__ == "__main__":
    main()
