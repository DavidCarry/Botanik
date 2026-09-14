"""Configuration lue depuis l'environnement.

Les valeurs par defaut visent le developpement local (docker compose).
Surcharger par variables d'environnement suffit a pointer vers d'autres
services -- une base Azure, par exemple -- sans toucher au code.
"""

import os

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

DB_URL = os.getenv(
    "DB_URL", "postgresql://botanik:botanik@localhost:5432/botanik"
)

# Periode de publication des mesures, en secondes
INTERVALLE_S = float(os.getenv("INTERVALLE_S", "5"))

TOPIC_MESURES = "botanik/mesures"
