"""Lecture des registres materiels.

`capteurs.yaml` et `actionneurs.yaml` sont la source de verite du projet :
les services y prennent ce qu'ils doivent piloter, l'API ce qu'elle doit
exposer. Un seul module les charge, pour que tous voient exactement la
meme chose -- sinon un capteur desactive pourrait disparaitre de l'ecran
tout en continuant d'etre publie.
"""

from pathlib import Path

import yaml

from config import MODE

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


def resoudre(elements, drivers) -> dict[str, dict]:
    """A chaque element du registre, le driver qui le sert et ses
    parametres -- selon MODE.

    Le publisher et le service des actionneurs faisaient ce travail
    chacun de leur cote, a l'identique : choisir le bloc `simule` ou
    `reel`, en extraire le nom du driver, ecarter ce qui n'est pas
    implemente. Deux copies d'une meme regle, c'est une regle qui finit
    par differer d'un service a l'autre.

    Un element dont le driver manque est ecarte avec un message plutot
    qu'en silence : le materiel arrive par morceaux, et il faut savoir
    lequel n'est pas encore branche.
    """
    retenus: dict[str, dict] = {}
    for e in elements:
        if MODE == "faux":
            driver = "simule"
            params = dict(e.get("simule") or {})
            # Le simulateur borne ses valeurs au domaine declare, la ou il
            # y en a un : du bruit ajoute a une valeur deja au plancher
            # produisait des lux negatifs.
            if "echelle" in e:
                params["echelle"] = e["echelle"]
        else:
            bloc = dict(e["reel"])
            driver, params = bloc.pop("driver"), bloc

        if driver not in drivers:
            print(f"{e['id']} ignore : driver '{driver}' non implemente",
                  flush=True)
            continue

        retenus[e["id"]] = {"driver": driver, "params": params}
    return retenus
