"""Etat de la machine qui heberge Botanik.

Separe des mesures de la serre : ce sont deux sujets differents, et on ne
surveille pas une carte comme on surveille une germination.
"""

import shutil
import time
from pathlib import Path

import psutil

DEMARRAGE = time.time()


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

    return {
        "horloge": time.strftime("%H:%M:%S"),
        "temperature_cpu": temperature_cpu(),
        "charge_cpu": round(psutil.cpu_percent(interval=None), 1),
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
    }
