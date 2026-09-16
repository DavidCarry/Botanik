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
from config import DB_URL, TOPIC_COMMANDES, TOPIC_MESURES

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
    print(f"Abonne a {TOPIC_MESURES}/# et {TOPIC_COMMANDES}/#", flush=True)


def on_message(client, conn, msg):
    identifiant = msg.topic.rsplit("/", 1)[-1]
    try:
        data = json.loads(msg.payload)
        valeur = float(data["valeur"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
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
    print("Connecte a la base", flush=True)

    # Rien a faire periodiquement : tout se joue dans on_message.
    service.executer(
        "Collecteur", periode=0.5, userdata=conn,
        on_connect=on_connect, on_message=on_message,
    )
    conn.close()


if __name__ == "__main__":
    main()
