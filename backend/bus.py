"""Liaison MQTT de l'API.

Elle emet les commandes, et ecoute en retour l'etat reel des actionneurs.
Un client unique, ouvert au demarrage et maintenu en vie, evite de
rouvrir une connexion au broker a chaque clic.

L'etat est garde en memoire et non en base : c'est une valeur courante,
pas un historique, et les messages retenus du broker la restituent en
quelques millisecondes au demarrage. L'historique des ordres, lui, est
deja dans la table `commandes`.

`connect_async` plutot que `connect` : l'API doit pouvoir demarrer meme
si le broker n'est pas encore la, et se raccrocher toute seule quand il
arrive. Sans cela, un ordre de demarrage malheureux -- l'API avant le
conteneur -- laisserait le service mort jusqu'au prochain redemarrage.
"""

import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

import service
from config import MQTT_HOST, MQTT_PORT, TOPIC_ETAT

_client: mqtt.Client | None = None

# Dernier etat connu de chaque actionneur, alimente par le broker.
_etats: dict[str, dict] = {}


def _on_connect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"Bus MQTT refuse : {reason_code}", flush=True)
        return
    # Les etats sont retenus cote broker : cet abonnement les recoit tous
    # dans la foulee, sans avoir a interroger qui que ce soit.
    client.subscribe(f"{TOPIC_ETAT}/#", qos=1)


def _on_message(client, userdata, msg):
    actionneur = msg.topic.rsplit("/", 1)[-1]
    try:
        _etats[actionneur] = json.loads(msg.payload)
    except json.JSONDecodeError:
        pass


def etats() -> dict[str, dict]:
    """Ce que les actionneurs ont annonce. Un actionneur absent n'a pas
    encore parle -- son service est peut-etre arrete."""
    return dict(_etats)


def demarrer():
    global _client
    _client = service.nouveau_client()
    _client.on_connect = _on_connect
    _client.on_message = _on_message
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
