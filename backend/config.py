"""Configuration lue depuis l'environnement.

Les valeurs par defaut visent le developpement local (docker compose).
Surcharger par variables d'environnement suffit a pointer vers d'autres
services -- une base Azure, par exemple -- sans toucher au code.
"""

import os

# "faux" : capteurs simules -- "reel" : materiel branche sur la Pi
MODE = os.getenv("MODE", "faux")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

DB_URL = os.getenv(
    "DB_URL", "postgresql://botanik:botanik@localhost:5432/botanik"
)

# Periode de publication des mesures, en secondes
INTERVALLE_S = float(os.getenv("INTERVALLE_S", "5"))

# Racines des topics MQTT. Un niveau par sens de circulation :
#   mesures/<capteur>      ce que la serre observe
#   commandes/<actionneur> ce qu'on lui demande
#   etat/<actionneur>      ce qu'elle fait vraiment
TOPIC_MESURES = "botanik/mesures"
TOPIC_COMMANDES = "botanik/commandes"
TOPIC_ETAT = "botanik/etat"
