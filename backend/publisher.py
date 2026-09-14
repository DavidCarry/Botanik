"""Publie des mesures simulees sur MQTT.

Tient lieu de capteurs tant qu'aucun materiel n'est branche. Le jour ou les
sondes arrivent, seule `lire_capteurs()` change : le reste de la chaine
(broker, collecteur, base, API) n'a pas a bouger.
"""

import json
import math
import random
import signal
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from config import INTERVALLE_S, MQTT_HOST, MQTT_PORT, TOPIC_MESURES

# Unite de chaque capteur, telle qu'elle part dans le payload
UNITES = {
    "humidite_sol_a": "%",
    "humidite_sol_b": "%",
    "temperature_air": "degC",
    "humidite_air": "%",
    "temperature_sol": "degC",
    "luminosite": "lux",
}

# L'humidite du sol derive lentement : on garde son etat entre deux tours
_humidite_sol = 55.0

_tourne = True


def _cycle_jour():
    """-1 au coeur de la nuit, +1 en milieu de journee."""
    maintenant = datetime.now()
    heure = maintenant.hour + maintenant.minute / 60
    return math.sin((heure - 6) / 24 * 2 * math.pi)


def lire_capteurs():
    """Renvoie {capteur: valeur}. Valeurs simulees, mais plausibles."""
    global _humidite_sol

    jour = _cycle_jour()

    # le sol seche, d'autant plus vite qu'il fait chaud et clair
    _humidite_sol -= 0.05 + 0.04 * max(jour, 0)
    _humidite_sol = max(_humidite_sol, 12.0)

    return {
        "humidite_sol_a": round(_humidite_sol + random.gauss(0, 0.3), 2),
        "humidite_sol_b": round(_humidite_sol - 2 + random.gauss(0, 0.3), 2),
        "temperature_air": round(21 + 3 * jour + random.gauss(0, 0.2), 2),
        "humidite_air": round(55 - 8 * jour + random.gauss(0, 1), 2),
        "temperature_sol": round(20 + 2 * jour + random.gauss(0, 0.1), 2),
        "luminosite": round(max(0.0, 7000 * jour + random.gauss(0, 150)), 1),
    }


def _arreter(signum, frame):
    global _tourne
    _tourne = False


def main():
    signal.signal(signal.SIGINT, _arreter)
    signal.signal(signal.SIGTERM, _arreter)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()
    print(f"Publisher connecte a {MQTT_HOST}:{MQTT_PORT}, "
          f"une mesure toutes les {INTERVALLE_S}s", flush=True)

    while _tourne:
        ts = datetime.now(timezone.utc).isoformat()
        for capteur, valeur in lire_capteurs().items():
            payload = {"valeur": valeur, "unite": UNITES[capteur], "ts": ts}
            client.publish(f"{TOPIC_MESURES}/{capteur}", json.dumps(payload))
        print(f"{ts} -- {len(UNITES)} mesures publiees", flush=True)
        time.sleep(INTERVALLE_S)

    client.loop_stop()
    client.disconnect()
    print("Publisher arrete", flush=True)


if __name__ == "__main__":
    main()
