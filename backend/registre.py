"""Lecture du registre des capteurs.

`capteurs.yaml` est la source de verite du projet : le publisher y prend
ce qu'il doit lire, l'API ce qu'elle doit exposer. Un seul module le
charge, pour que les deux voient exactement la meme chose -- sinon un
capteur desactive pourrait disparaitre de l'ecran tout en continuant
d'etre publie.
"""

from pathlib import Path

import yaml

FICHIER = Path(__file__).parent / "capteurs.yaml"


def capteurs_actifs():
    """Les capteurs declares `actif: true`, dans l'ordre du fichier.

    Relu a chaque appel : le fichier tient en quelques lignes, et pouvoir
    activer un capteur sans redemarrer l'API vaut mieux qu'un cache.
    """
    with open(FICHIER, encoding="utf-8") as f:
        declares = yaml.safe_load(f)["capteurs"]
    return [c for c in declares if c.get("actif", False)]
