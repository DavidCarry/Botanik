"""Ecoute les commandes sur MQTT et actionne le materiel.

Miroir exact de publisher.py : celui-la lit le monde et le publie,
celui-ci ecoute des ordres et agit dessus. Il ne connait aucun actionneur
en particulier -- il parcourt le registre et appelle le driver indique.

Apres chaque action, il republie l'etat ATTEINT sur botanik/etat/<id>.
C'est ce qui separe un interrupteur qui affiche ce qu'il croit d'un
interrupteur qui affiche ce qui est : l'ecran n'attend plus sa propre
supposition, il attend la reponse du materiel.
"""

import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

import registre
import service
from config import MODE, TOPIC_COMMANDES, TOPIC_ETAT
from drivers import SORTIES


def charger_actionneurs():
    """Les actionneurs actifs, chacun avec le driver qui l'actionnera."""
    return registre.resoudre(registre.actionneurs_actifs(), SORTIES)


def annoncer(client: mqtt.Client, actionneur: str, valeur: float):
    """Publie l'etat d'un actionneur, en message retenu.

    `retain=True` est essentiel : le broker garde le dernier etat de
    chaque actionneur et le sert immediatement a tout nouvel abonne.
    Sans cela, une API qui redemarre ne saurait plus si la pompe tourne
    avant la prochaine commande -- et l'ecran resterait aveugle.
    """
    charge = {
        "valeur": valeur,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    client.publish(f"{TOPIC_ETAT}/{actionneur}", json.dumps(charge),
                   qos=1, retain=True)


def main():
    actionneurs = charger_actionneurs()
    if not actionneurs:
        print("Aucun actionneur actif dans actionneurs.yaml", flush=True)
        return

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f"Connexion MQTT refusee : {reason_code}", flush=True)
            return
        client.subscribe(f"{TOPIC_COMMANDES}/#", qos=1)
        print(f"Abonne a {TOPIC_COMMANDES}/#", flush=True)

        # Au demarrage, tout est au repos : on l'annonce plutot que de
        # laisser l'ecran deviner. Un etat retenu d'une session
        # precedente serait devenu faux au redemarrage de la machine.
        for actionneur in actionneurs:
            annoncer(client, actionneur, 0.0)

    def on_message(client, userdata, msg):
        actionneur = msg.topic.rsplit("/", 1)[-1]
        cible = actionneurs.get(actionneur)
        if cible is None:
            print(f"Commande ignoree : {actionneur} inconnu ou inactif",
                  flush=True)
            return

        try:
            valeur = float(json.loads(msg.payload)["valeur"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            print(f"Commande illisible sur {msg.topic} : {e}", flush=True)
            return

        try:
            atteint = SORTIES[cible["driver"]].appliquer(
                actionneur, valeur, cible["params"]
            )
        except Exception as e:
            # Un actionneur qui refuse ne doit pas emporter les autres :
            # on n'annonce simplement aucun etat, et l'ecran le montrera.
            print(f"Echec sur {actionneur} : {e}", flush=True)
            return

        annoncer(client, actionneur, atteint)
        print(f"{actionneur} -> {atteint}", flush=True)

    print(f"Actionneurs : mode {MODE}, {len(actionneurs)} pilotes", flush=True)
    service.executer(
        "Actionneurs", periode=0.5,
        on_connect=on_connect, on_message=on_message,
    )


if __name__ == "__main__":
    main()
