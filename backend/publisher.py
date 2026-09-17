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


# Capteurs actuellement en repli, pour n'annoncer que les bascules.
# Sans cela, une sonde debranchee remplirait le journal de deux lignes
# par seconde et noierait tout le reste.
_en_repli: set[str] = set()


def lire_capteurs(capteurs):
    """La valeur de chaque capteur, et si elle vient d'une vraie sonde.

    Une sonde qui ne repond plus ne fait pas disparaitre sa mesure : on
    bascule sur la valeur simulee, et la mesure emporte la mention. Un
    ecran qui se vide en cours de demonstration ne dit rien de ce qui se
    passe ; un ecran qui affiche « simule » le dit exactement.

    Le repli est tente a CHAQUE cycle : une nappe qu'on rebranche reprend
    donc d'elle-meme, sans redemarrage.
    """
    valeurs = {}
    for c in capteurs:
        identifiant = c["id"]
        try:
            valeurs[identifiant] = (DRIVERS[c["driver"]].lire(identifiant, c["params"]),
                                    c["source"] == "simule")
            if identifiant in _en_repli:
                _en_repli.discard(identifiant)
                print(f"{identifiant} repond de nouveau, retour a la sonde reelle",
                      flush=True)
            continue
        except Exception as e:
            repli = c.get("repli")
            if repli is None:
                print(f"Capteur {identifiant} illisible : {e}", flush=True)
                continue
            if identifiant not in _en_repli:
                _en_repli.add(identifiant)
                print(f"{identifiant} illisible ({e}) -- bascule sur la simulation",
                      flush=True)

        try:
            valeurs[identifiant] = (
                DRIVERS[repli["driver"]].lire(identifiant, repli["params"]), True)
        except Exception as e:
            print(f"Capteur {identifiant} : repli impossible non plus ({e})",
                  flush=True)
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
        for capteur, (valeur, simule) in valeurs.items():
            payload = {"valeur": valeur, "unite": unites[capteur], "ts": ts,
                       # La mesure dit d'ou elle vient : c'est elle qui
                       # voyage jusqu'a l'ecran, pas le registre.
                       "simule": simule}
            client.publish(f"{TOPIC_MESURES}/{capteur}", json.dumps(payload))
        print(f"{ts} -- {len(valeurs)} mesures publiees", flush=True)

    print(f"Publisher connecte a {MQTT_HOST}:{MQTT_PORT} -- mode {MODE}, "
          f"{len(capteurs)} capteurs, toutes les {INTERVALLE_S}s", flush=True)
    service.executer("Publisher", periode=INTERVALLE_S, travail=publier)


if __name__ == "__main__":
    main()
