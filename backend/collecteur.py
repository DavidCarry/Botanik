"""Ecoute les mesures sur MQTT et les archive en base.

Seul composant a ecrire dans `mesures`. Un message malforme est ignore avec
un avertissement : le collecteur ne doit jamais s'arreter a cause d'un
capteur qui deraille.
"""

import json
from datetime import datetime, timezone

import psycopg

import service
from config import DB_URL, TOPIC_MESURES

INSERTION = (
    "INSERT INTO mesures (ts, capteur, valeur, unite) VALUES (%s, %s, %s, %s)"
)


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
    print(f"Abonne a {TOPIC_MESURES}/#", flush=True)


def on_message(client, conn, msg):
    capteur = msg.topic.rsplit("/", 1)[-1]
    try:
        data = json.loads(msg.payload)
        valeur = float(data["valeur"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        print(f"Message ignore sur {msg.topic} : {e}", flush=True)
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                INSERTION,
                (_horodatage(data.get("ts")), capteur, valeur, data.get("unite")),
            )
        print(f"{capteur} = {valeur} {data.get('unite', '')}", flush=True)
    except psycopg.Error as e:
        print(f"Echec d'insertion pour {capteur} : {e}", flush=True)
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
