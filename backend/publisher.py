"""Lit les capteurs declares dans capteurs.yaml et les publie sur MQTT.

Ne connait aucun capteur en particulier : il parcourt le registre et appelle
le driver indique. Brancher une nouvelle sonde ne demande donc aucune
modification ici -- seulement une entree dans capteurs.yaml, et un driver
dans drivers/ si son type est nouveau.
"""

import json
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
import yaml

from config import INTERVALLE_S, MODE, MQTT_HOST, MQTT_PORT, TOPIC_MESURES
from drivers import DRIVERS

REGISTRE = Path(__file__).parent / "capteurs.yaml"

_tourne = True


def charger_capteurs():
    """Resout le registre selon MODE et ne garde que les capteurs actifs."""
    with open(REGISTRE, encoding="utf-8") as f:
        declares = yaml.safe_load(f)["capteurs"]

    retenus = []
    for c in declares:
        if not c.get("actif", False):
            continue

        if MODE == "faux":
            driver, params = "simule", c["simule"]
        else:
            bloc = dict(c["reel"])
            driver, params = bloc.pop("driver"), bloc

        if driver not in DRIVERS:
            print(f"{c['id']} ignore : driver '{driver}' non implemente",
                  flush=True)
            continue

        retenus.append(
            {"id": c["id"], "unite": c["unite"], "driver": driver,
             "params": params}
        )
    return retenus


def lire_capteurs(capteurs):
    """Un capteur illisible est signale, les autres continuent d'etre lus."""
    valeurs = {}
    for c in capteurs:
        try:
            valeurs[c["id"]] = DRIVERS[c["driver"]].lire(c["id"], c["params"])
        except Exception as e:
            print(f"Capteur {c['id']} illisible : {e}", flush=True)
    return valeurs


def _arreter(signum, frame):
    global _tourne
    _tourne = False


def main():
    signal.signal(signal.SIGINT, _arreter)
    signal.signal(signal.SIGTERM, _arreter)

    capteurs = charger_capteurs()
    if not capteurs:
        print("Aucun capteur actif dans capteurs.yaml", flush=True)
        return
    unites = {c["id"]: c["unite"] for c in capteurs}

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()
    print(f"Publisher connecte a {MQTT_HOST}:{MQTT_PORT} -- mode {MODE}, "
          f"{len(capteurs)} capteurs, toutes les {INTERVALLE_S}s", flush=True)

    while _tourne:
        ts = datetime.now(timezone.utc).isoformat()
        valeurs = lire_capteurs(capteurs)
        for capteur, valeur in valeurs.items():
            payload = {"valeur": valeur, "unite": unites[capteur], "ts": ts}
            client.publish(f"{TOPIC_MESURES}/{capteur}", json.dumps(payload))
        print(f"{ts} -- {len(valeurs)} mesures publiees", flush=True)
        time.sleep(INTERVALLE_S)

    client.loop_stop()
    client.disconnect()
    print("Publisher arrete", flush=True)


if __name__ == "__main__":
    main()
