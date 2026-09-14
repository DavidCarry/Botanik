"""Ecoute les mesures sur MQTT et les archive en base.

Seul composant a ecrire dans `mesures`. Un message malforme est ignore avec
un avertissement : le collecteur ne doit jamais s'arreter a cause d'un
capteur qui deraille.
"""

import json
import signal
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psycopg

from config import DB_URL, MQTT_HOST, MQTT_PORT, TOPIC_MESURES

INSERTION = (
    "INSERT INTO mesures (ts, capteur, valeur, unite) VALUES (%s, %s, %s, %s)"
)

_tourne = True


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


def _arreter(signum, frame):
    global _tourne
    _tourne = False


def main():
    signal.signal(signal.SIGINT, _arreter)
    signal.signal(signal.SIGTERM, _arreter)

    conn = psycopg.connect(DB_URL, autocommit=True)
    print("Connecte a la base", flush=True)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=conn)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    while _tourne:
        time.sleep(0.5)

    client.loop_stop()
    client.disconnect()
    conn.close()
    print("Collecteur arrete", flush=True)


if __name__ == "__main__":
    main()
