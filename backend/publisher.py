"""Lit les capteurs declares dans capteurs.yaml et les publie sur MQTT.

Ne connait aucun capteur en particulier : il parcourt le registre et appelle
le driver indique. Brancher une nouvelle sonde ne demande donc aucune
modification ici -- seulement une entree dans capteurs.yaml, et un driver
dans drivers/ si son type est nouveau.
"""

import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

import registre
import service
from config import INTERVALLE_S, MODE, MQTT_HOST, MQTT_PORT, TOPIC_MESURES
from drivers import DRIVERS


def charger_capteurs():
    """Les capteurs actifs, chacun avec son driver et son unite."""
    actifs = registre.capteurs_actifs()
    resolus = registre.resoudre(actifs, DRIVERS)
    return [
        {"id": c["id"], "unite": c["unite"], **resolus[c["id"]]}
        for c in actifs if c["id"] in resolus
    ]


def lire_capteurs(capteurs):
    """Un capteur illisible est signale, les autres continuent d'etre lus."""
    valeurs = {}
    for c in capteurs:
        try:
            valeurs[c["id"]] = DRIVERS[c["driver"]].lire(c["id"], c["params"])
        except Exception as e:
            print(f"Capteur {c['id']} illisible : {e}", flush=True)
    return valeurs


def main():
    capteurs = charger_capteurs()
    if not capteurs:
        print("Aucun capteur actif dans capteurs.yaml", flush=True)
        return
    unites = {c["id"]: c["unite"] for c in capteurs}

    def publier(client: mqtt.Client):
        ts = datetime.now(timezone.utc).isoformat()
        valeurs = lire_capteurs(capteurs)
        for capteur, valeur in valeurs.items():
            payload = {"valeur": valeur, "unite": unites[capteur], "ts": ts}
            client.publish(f"{TOPIC_MESURES}/{capteur}", json.dumps(payload))
        print(f"{ts} -- {len(valeurs)} mesures publiees", flush=True)

    print(f"Publisher connecte a {MQTT_HOST}:{MQTT_PORT} -- mode {MODE}, "
          f"{len(capteurs)} capteurs, toutes les {INTERVALLE_S}s", flush=True)
    service.executer("Publisher", periode=INTERVALLE_S, travail=publier)


if __name__ == "__main__":
    main()
