"""Emission MQTT depuis l'API.

L'API n'ecoute rien : elle ne fait qu'emettre des commandes. Un client
unique, ouvert au demarrage et maintenu en vie, evite de rouvrir une
connexion au broker a chaque clic.

`connect_async` plutot que `connect` : l'API doit pouvoir demarrer meme
si le broker n'est pas encore la, et se raccrocher toute seule quand il
arrive. Sans cela, un ordre de demarrage malheureux -- l'API avant le
conteneur -- laisserait le service mort jusqu'au prochain redemarrage.
"""

import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from config import MQTT_HOST, MQTT_PORT

_client: mqtt.Client | None = None


def demarrer():
    global _client
    _client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    _client.connect_async(MQTT_HOST, MQTT_PORT)
    # Reprise progressive : on ne martele pas un broker qui redemarre.
    _client.reconnect_delay_set(min_delay=1, max_delay=30)
    _client.loop_start()
    print(f"Bus MQTT vers {MQTT_HOST}:{MQTT_PORT}", flush=True)


def arreter():
    if _client:
        _client.loop_stop()
        _client.disconnect()


def publier(topic: str, contenu: dict) -> bool:
    """Depose un message et dit s'il est bien parti.

    QoS 1 : une commande doit arriver. En QoS 0, un message emis pendant
    une coupure serait jete sans bruit -- l'ecran afficherait une pompe
    demarree qui ne tourne pas.

    L'horodatage est pose ici, a la source, et non par celui qui recoit :
    c'est l'instant de la demande qui fait foi.
    """
    # La liaison est verifiee AVANT de publier, et non apres. En QoS 1,
    # paho met en file d'attente un message emis hors connexion et le
    # poste a la reconnexion : l'appelant recevrait un echec, puis la
    # pompe demarrerait trente secondes plus tard, toute seule. Refuser
    # en amont est le seul moyen de garantir qu'un echec signifie bien
    # que rien ne partira.
    if _client is None or not _client.is_connected():
        return False
    charge = {**contenu, "ts": datetime.now(timezone.utc).isoformat()}
    info = _client.publish(topic, json.dumps(charge), qos=1)
    return info.rc == mqtt.MQTT_ERR_SUCCESS
