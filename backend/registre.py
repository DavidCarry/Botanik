"""Lecture des registres materiels.

`capteurs.yaml` et `actionneurs.yaml` sont la source de verite du projet :
les services y prennent ce qu'ils doivent piloter, l'API ce qu'elle doit
exposer. Un seul module les charge, pour que tous voient exactement la
meme chose -- sinon un capteur desactive pourrait disparaitre de l'ecran
tout en continuant d'etre publie.
"""

from pathlib import Path

import yaml

ICI = Path(__file__).parent
CAPTEURS = ICI / "capteurs.yaml"
ACTIONNEURS = ICI / "actionneurs.yaml"


def _actifs(fichier, cle):
    """Les entrees declarees `actif: true`, dans l'ordre du fichier.

    Relu a chaque appel : ces fichiers tiennent en quelques lignes, et
    pouvoir activer un element sans redemarrer l'API vaut mieux qu'un
    cache.
    """
    with open(fichier, encoding="utf-8") as f:
        declares = yaml.safe_load(f)[cle]
    return [e for e in declares if e.get("actif", False)]


def capteurs_actifs():
    return _actifs(CAPTEURS, "capteurs")


def actionneurs_actifs():
    return _actifs(ACTIONNEURS, "actionneurs")
