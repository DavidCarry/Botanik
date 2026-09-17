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
    parametres -- plus la mention de ce qu'on a reellement obtenu.

    Le publisher et le service des actionneurs faisaient ce travail
    chacun de leur cote, a l'identique : choisir le bloc `simule` ou
    `reel`, en extraire le nom du driver, ecarter ce qui n'est pas
    implemente. Deux copies d'une meme regle, c'est une regle qui finit
    par differer d'un service a l'autre.

    Le repli est par ELEMENT, et c'est ce qui rend le branchement
    progressif possible : en MODE=reel, un capteur dont le driver
    n'existe pas encore retombe en simulation au lieu de disparaitre de
    l'ecran. On peut donc cabler les sondes une par une sans perdre la
    moitie du tableau de bord a chaque etape.

    `source` dit lequel des deux on a obtenu. Il remonte jusqu'a
    l'interface : afficher une valeur inventee sans le dire vaudrait
    mieux ne rien afficher du tout.
    """
    retenus: dict[str, dict] = {}
    for e in elements:
        bloc = dict(e.get("reel") or {})
        driver = bloc.pop("driver", None)
        params = bloc
        source = "reel"

        # `simuler: true` garde un element en simulation meme en mode reel.
        # C'est l'interrupteur du branchement progressif : on valide une
        # sonde a la fois, sans toucher au reste du registre ni devoir
        # inventer un faux driver pour les autres.
        retenu_simule = bool(e.get("simuler"))

        if MODE == "faux" or retenu_simule or driver not in drivers:
            if MODE != "faux":
                raison = ("garde en simulation par le registre" if retenu_simule
                          else f"driver '{driver}' absent, repli sur la simulation")
                print(f"{e['id']} : {raison}", flush=True)
            driver, source = "simule", "simule"
            params = dict(e.get("simule") or {})

        if driver not in drivers:
            print(f"{e['id']} ignore : aucun driver, pas meme simule",
                  flush=True)
            continue

        # L'echelle appartient au capteur, pas au driver : elle sert au
        # simulateur pour borner son bruit comme au convertisseur pour
        # etendre une mesure brute. On la transmet dans les deux cas.
        if "echelle" in e:
            params["echelle"] = e["echelle"]

        retenus[e["id"]] = {"driver": driver, "params": params,
                            "source": source}

        # Un element reel emporte de quoi se rabattre sur la simulation
        # si la sonde ne repond plus. Le choix du driver se fait au
        # demarrage, mais une nappe qui se debranche, elle, n'attend pas
        # le redemarrage pour arriver.
        if source == "reel":
            replis = dict(e.get("simule") or {})
            if "echelle" in e:
                replis["echelle"] = e["echelle"]
            retenus[e["id"]]["repli"] = {"driver": "simule", "params": replis}
    return retenus
