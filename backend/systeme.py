"""Etat de la machine qui heberge Botanik.

Separe des mesures de la serre : ce sont deux sujets differents, et on ne
surveille pas une carte comme on surveille une germination.

Tout ce qui peut etre LU l'est reellement. Ce qui ne peut pas l'etre --
la temperature du processeur n'existe pas sous Windows, par exemple --
est remplace par une valeur plausible, et la reponse DIT lesquelles :
un tableau de bord qui invente sans le dire ne vaut rien.
"""

import math
import random
import shutil
import time
from pathlib import Path

import psutil

DEMARRAGE = time.time()

# Duree de mesure de la charge processeur.
#
# `cpu_percent(interval=None)` rend le pourcentage ecoule DEPUIS LE
# DERNIER APPEL -- et zero au tout premier, faute de point de depart.
# Comme cette route n'est appelee qu'a l'ouverture du panneau, elle
# affichait donc 0,0 % la premiere fois, puis une moyenne sur plusieurs
# minutes. Mesurer sur un court intervalle donne la charge du moment,
# ce que le panneau pretend montrer. La route s'execute hors de la
# boucle asynchrone : ces 150 ms ne bloquent personne.
MESURE_CHARGE_S = 0.15


def _plausible(base: float, amplitude: float, periode_s: float) -> float:
    """Une valeur qui derive lentement, quand on ne peut pas la mesurer.

    Une constante se repererait tout de suite comme fausse ; du bruit pur
    donnerait l'illusion d'une mesure. Une lente oscillation est ce qui
    ressemble le plus a un vrai releve -- et c'est bien pourquoi la
    reponse precise ailleurs qu'elle est inventee.
    """
    phase = (time.time() % periode_s) / periode_s * 2 * math.pi
    return round(base + amplitude * math.sin(phase) + random.gauss(0, 0.3), 1)


def temperature_cpu():
    """Degres Celsius, ou None hors Raspberry Pi (Windows, par exemple)."""
    try:
        brut = Path("/sys/class/thermal/thermal_zone0/temp").read_text()
        return round(int(brut) / 1000, 1)
    except (OSError, ValueError):
        capteurs = getattr(psutil, "sensors_temperatures", lambda: {})()
        for releves in capteurs.values():
            if releves:
                return round(releves[0].current, 1)
        return None


def etat():
    memoire = psutil.virtual_memory()
    disque = shutil.disk_usage("/")

    # Les grandeurs qu'on n'a pas pu lire et qu'on a donc inventees.
    simules = []

    temperature = temperature_cpu()
    if temperature is None:
        temperature = _plausible(52.0, 6.0, 180)
        simules.append("temperature_cpu")

    return {
        "horloge": time.strftime("%H:%M:%S"),
        "temperature_cpu": temperature,
        "charge_cpu": round(psutil.cpu_percent(interval=MESURE_CHARGE_S), 1),
        "coeurs": psutil.cpu_count(logical=True),
        "memoire": {
            "utilisee_go": round(memoire.used / 1e9, 2),
            "totale_go": round(memoire.total / 1e9, 2),
            "part": round(memoire.percent, 1),
        },
        "disque": {
            "utilise_go": round(disque.used / 1e9, 1),
            "total_go": round(disque.total / 1e9, 1),
            "part": round(disque.used / disque.total * 100, 1),
        },
        # Duree depuis le demarrage du service, pas de la machine :
        # c'est ce qui dit si l'application a redemarre.
        "en_ligne_s": round(time.time() - DEMARRAGE),
        # Les champs ci-dessus qui ne viennent PAS d'une mesure reelle.
        "simules": simules,
    }
