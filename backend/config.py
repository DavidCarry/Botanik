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

# ---- Camera ----
#
# En memoire et non sur la carte SD : soixante-dix kilo-octets par
# seconde useraient la carte en quelques mois, pour des images que
# personne ne relit.
CAMERA_FICHIER = os.getenv("CAMERA_FICHIER", "/dev/shm/botanik/vue.jpg")
# Une prise toutes les 100 ms, soit dix images par seconde. La camera
# en accepterait quarante ; dix suffisent a lire comme du mouvement, et
# coutent un quart de coeur sur les quatre de la Pi.
CAMERA_S = float(os.getenv("CAMERA_S", "0.1"))
CAMERA_TAILLE = (1280, 720)

# Rotation a appliquer, en degres : 0 ou 180 selon le sens de montage du
# module. Une camera fixee tete en bas donne une image renversee, et la
# retourner dans le navigateur ferait porter au client un probleme de
# visserie.
CAMERA_ROTATION = int(os.getenv("CAMERA_ROTATION", "0"))

# Au-dela, la derniere vue est consideree comme perimee et l'ecran le
# dit plutot que de la faire passer pour du direct.
CAMERA_FRAICHEUR_S = float(os.getenv("CAMERA_FRAICHEUR_S", "10"))

# ---- Visages ----
#
# Un agrement, pas un organe de la serre : si ce service s'arrete, la
# vue reste, et rien d'autre ne s'en apercoit.
VISAGES_MODELE = os.getenv("VISAGES_MODELE", "modeles/visages-yunet.onnx")

# Une image sur deux parmi celles de la camera. Les regarder toutes
# doublerait le cout pour un cadre qui suivrait les tetes vingt
# centiemes de seconde plus tot -- ce que personne ne remarque, alors
# qu'un demi-coeur pris en permanence, si.
VISAGES_S = float(os.getenv("VISAGES_S", "0.2"))

# La detection travaille sur une image REDUITE a cette largeur. A 1280
# elle coute quatre fois plus cher pour ne rien voir de plus : un visage
# a portee de la serre fait encore une centaine de pixels a 640.
VISAGES_LARGEUR = 640

# En dessous, on ne retient pas : mieux vaut manquer un visage de dos
# qu'encadrer un pot de fleurs.
VISAGES_SCORE = float(os.getenv("VISAGES_SCORE", "0.8"))

# Un visage perdu une image ou deux -- un clignement, un mouvement de
# tete -- reste affiche ce laps de temps. Sans cela le cadre papillote
# en permanence, ce qui se remarque bien plus qu'un leger retard.
VISAGES_MEMOIRE_S = float(os.getenv("VISAGES_MEMOIRE_S", "0.5"))

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

# Un simple signal : « les regles ont change, relis-les ». Le contenu du
# message n'a aucune importance -- la base reste la source de verite, et
# deux services qui se passeraient les regles par MQTT finiraient par
# diverger.
TOPIC_REGLES = "botanik/regles"

# Les visages vus dans la derniere image, en coordonnees RELATIVES a
# l'image (de 0 a 1). L'interface les pose ensuite sur la vue, quelle
# que soit sa taille a l'ecran -- des pixels obligeraient chacun a
# savoir en quelle resolution la camera filme.
TOPIC_VISAGES = "botanik/visages"
