"""Driver de simulation : se comporte comme du materiel qui n'existe pas.

En lecture, produit des valeurs plausibles ; en ecriture, accepte l'ordre
et le retient. Sert tant que rien n'est branche, et reste disponible
ensuite comme repli -- si une sonde lache pendant une demonstration,
basculer MODE=faux laisse le reste de la chaine fonctionner.
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


# Etat courant des sorties simulees, indexe par actionneur
_sorties = {}


def appliquer(actionneur_id, valeur, params):
    """Accepte l'ordre et renvoie l'etat atteint.

    Un driver reel renverrait ce qu'il a pu faire, pas ce qu'on lui a
    demande -- c'est la difference entre un retour d'etat et un echo. Ici
    les deux coincident, faute de materiel pour les faire diverger.
    """
    _sorties[actionneur_id] = float(valeur)
    return _sorties[actionneur_id]
