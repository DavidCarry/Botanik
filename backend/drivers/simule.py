"""Driver de simulation : produit des valeurs plausibles sans materiel.

Sert tant que les sondes ne sont pas branchees, et reste disponible ensuite
comme repli -- si un capteur lache pendant une demonstration, basculer
MODE=faux laisse le reste de la chaine fonctionner.
"""

import math
import random
from datetime import datetime

# Etat des profils qui derivent dans le temps, indexe par capteur
_etats = {}


def _cycle_jour():
    """-1 au coeur de la nuit, +1 en milieu de journee."""
    maintenant = datetime.now()
    heure = maintenant.hour + maintenant.minute / 60
    return math.sin((heure - 6) / 24 * 2 * math.pi)


def lire(capteur_id, params):
    profil = params["profil"]
    bruit = params.get("bruit", 0)

    if profil == "cycle_jour":
        valeur = params["base"] + params["amplitude"] * _cycle_jour()

    elif profil == "lumiere":
        valeur = max(0.0, params["maximum"] * _cycle_jour())

    elif profil == "decroissant":
        # seche d'autant plus vite qu'il fait jour
        courant = _etats.get(capteur_id, params["depart"])
        courant -= params["vitesse"] * (1 + max(_cycle_jour(), 0))
        courant = max(courant, params["plancher"])
        _etats[capteur_id] = courant
        valeur = courant

    else:
        raise ValueError(f"profil inconnu : {profil}")

    return round(valeur + random.gauss(0, bruit), 2)
