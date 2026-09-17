"""Configuration lue depuis l'environnement.

Les valeurs par defaut visent le developpement local (docker compose).
Surcharger par variables d'environnement suffit a pointer vers d'autres
services -- une base Azure, par exemple -- sans toucher au code.
"""

import os
from pathlib import Path


def _charger_env():
    """Lit le .env de la racine s'il existe.

    Les variables deja posees par le systeme l'emportent : en production,
    systemd ou Docker doivent pouvoir surcharger le fichier sans avoir a
    le modifier. Pas de dependance : trois lignes suffisent, et une de
    moins a installer sur la Pi.
    """
    fichier = Path(__file__).parent.parent / ".env"
    if not fichier.is_file():
        return
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        os.environ.setdefault(cle.strip(), valeur.strip())


_charger_env()

# "faux" : capteurs simules -- "reel" : materiel branche sur la Pi
MODE = os.getenv("MODE", "faux")

# 127.0.0.1 et non "localhost" : ce nom resout ::1 AVANT 127.0.0.1, et
# Docker ne publie ces ports que sur IPv4. Chaque connexion perdait deux
# secondes a echouer en IPv6 avant de retomber sur IPv4 -- de quoi rendre
# le pilotage poussif et faire expirer l'attente cote navigateur.
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Le broker refuse les anonymes. Vide = pas d'identification, ce qui ne
# sert qu'a diagnostiquer : le broker rejettera la connexion.
MQTT_UTILISATEUR = os.getenv("MQTT_UTILISATEUR", "")
MQTT_MDP = os.getenv("MQTT_MDP", "")

DB_URL = os.getenv(
    "DB_URL", "postgresql://botanik:botanik@127.0.0.1:5432/botanik"
)

# ---- Trois cadences, et une seule raison pour chacune ----
#
# Lire un capteur ne coute presque rien ; l'ecrire en base coute de la
# place, pour toujours. Les deux n'ont donc pas a suivre le meme rythme,
# et les confondre obligeait a choisir entre un ecran qui traine et une
# carte SD qui se remplit.

# Lecture des capteurs et diffusion sur MQTT : ce que voit le tableau de
# bord, pousse par le flux. Deux fois par seconde, on suit un doigt pose
# sur la sonde.
INTERVALLE_S = float(os.getenv("INTERVALLE_S", "0.5"))

# Ecriture en base : ce que montrent les courbes. Un point toutes les
# cinq minutes fait 288 releves par jour et par capteur -- de quoi lire
# une journee sans trou, pour environ trois megaoctets par mois.
ARCHIVAGE_S = float(os.getenv("ARCHIVAGE_S", "300"))

# Garde-fou de stockage. Sous ce seuil d'espace libre, le collecteur
# efface les mesures les plus anciennes : perdre l'histoire vaut mieux
# que de ne plus pouvoir enregistrer le present.
ESPACE_MINIMAL_GO = float(os.getenv("ESPACE_MINIMAL_GO", "1.5"))

# Racines des topics MQTT. Un niveau par sens de circulation :
#   mesures/<capteur>      ce que la serre observe
#   commandes/<actionneur> ce qu'on lui demande
#   etat/<actionneur>      ce qu'elle fait vraiment
#   alertes/<grandeur>     ce qui ne va pas, et depuis quand
TOPIC_MESURES = "botanik/mesures"
TOPIC_COMMANDES = "botanik/commandes"
TOPIC_ETAT = "botanik/etat"
TOPIC_ALERTES = "botanik/alertes"
