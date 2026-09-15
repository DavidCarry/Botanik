"""Ossature commune aux services MQTT.

Le publisher et le collecteur different par ce qu'ils font ; tout le
reste -- se connecter au broker, tourner jusqu'a ce qu'on les arrete,
se fermer proprement -- etait ecrit deux fois a l'identique.
"""

import signal
import time

import paho.mqtt.client as mqtt

from config import MQTT_HOST, MQTT_PORT


def executer(nom, *, periode, travail=None, userdata=None,
             on_connect=None, on_message=None):
    """Connecte un client MQTT et boucle jusqu'a SIGINT ou SIGTERM.

    `travail(client)` est rappele toutes les `periode` secondes ; un
    service qui ne fait que reagir aux messages n'en passe pas.

    systemd envoie SIGTERM a l'arret : sans ce traitement, le processus
    serait tue net, au milieu d'une publication ou d'une insertion.
    """
    tourne = True

    def arreter(signum, frame):
        nonlocal tourne
        tourne = False

    signal.signal(signal.SIGINT, arreter)
    signal.signal(signal.SIGTERM, arreter)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
    if on_connect:
        client.on_connect = on_connect
    if on_message:
        client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    while tourne:
        if travail:
            travail(client)
        # Sommeil fractionne : un arret demande pendant l'attente est pris
        # en compte tout de suite, et non a la fin de la periode.
        fin = time.monotonic() + periode
        while tourne and time.monotonic() < fin:
            time.sleep(max(0.0, min(0.25, fin - time.monotonic())))

    client.loop_stop()
    client.disconnect()
    print(f"{nom} arrete", flush=True)
