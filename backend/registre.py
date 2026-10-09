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


# Les grandeurs qui ne sortent d'aucun capteur.
#
# `eclairement_jour` est un cumul recalcule depuis l'archive -- le temps
# passe sous une lumiere suffisante depuis minuit -- et `heure` est
# simplement l'heure qu'il est. Aucune des deux n'a de ligne dans
# capteurs.yaml, et il faut pourtant savoir les nommer et les borner :
# le reseau les prend en entree, et l'API les expose au meme titre que
# les mesures.
#
# Memes trois champs qu'une entree de capteurs.yaml, pour que tout ce
# qui decrit une grandeur se lise pareil, d'ou qu'elle vienne.
#
# Declarees ICI et nulle part ailleurs : `donnees.HORS_REGISTRE` en tire
# les bornes qui normalisent les entrees du reseau. Deux echelles qui
# doivent rester egales finiraient par diverger.
HORS_CAPTEUR = {
    "eclairement_jour": {
        "libelle": "Lumière reçue",
        "unite": "h",
        "echelle": {"min": 0.0, "max": 24.0},
    },
    "heure": {
        "libelle": "Heure",
        "unite": "h",
        "echelle": {"min": 0.0, "max": 24.0},
    },
}


# Broches occupees par les bus, quel que soit le registre. Les declarer
# permet de refuser une collision avec l'I2C ou le SPI, qu'aucun fichier
# du projet ne mentionne mais qui sont bien cablees.
BROCHES_RESERVEES = {
    2: "I2C (SDA)", 3: "I2C (SCL)",
    4: "1-Wire",
    8: "SPI (CE0)", 9: "SPI (MISO)", 10: "SPI (MOSI)", 11: "SPI (SCLK)",
}


def collisions() -> list[str]:
    """Les broches revendiquees par deux elements actifs a la fois.

    Ce controle a ete ecrit apres coup, et deux fois plutot qu'une : un
    telemetre pose sur les broches de deux LED les faisait clignoter au
    rythme de ses impulsions, et une lampe declaree sur la broche du
    buzzer attendait tranquillement qu'on l'active. Rien ne protestait --
    c'est le premier service demarre qui gagnait la broche, et le second
    echouait sur un « GPIO busy » incomprehensible.

    On regarde tout ce qui est ACTIF, capteurs et actionneurs ensemble :
    une broche ne sait pas qui la tient.
    """
    pris: dict[int, list[str]] = {}
    for element in capteurs_actifs() + actionneurs_actifs():
        bloc = element.get("reel") or {}
        for cle, valeur in bloc.items():
            if cle in ("broche", "trigger", "echo") and isinstance(valeur, int):
                pris.setdefault(valeur, []).append(f"{element['id']}.{cle}")

    plaintes = []
    for broche, porteurs in sorted(pris.items()):
        if len(porteurs) > 1:
            plaintes.append(f"GPIO {broche} revendiquee par {' et '.join(porteurs)}")
        elif broche in BROCHES_RESERVEES:
            plaintes.append(f"GPIO {broche} ({porteurs[0]}) est deja "
                            f"{BROCHES_RESERVEES[broche]}")
    return plaintes


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
