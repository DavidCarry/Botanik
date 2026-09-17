"""Driver du convertisseur analogique-numerique MCP3004, en SPI.

Les quatre capteurs de la serre sont analogiques et passent tous par
cette meme puce : un fil par grandeur, une voie par fil. Un seul module
les sert donc tous -- quatre fichiers qui liraient la meme puce sur
quatre voies differentes n'auraient rien dit de plus.

La puce ne rend qu'un rapport de tension, entre 0 et 1. La transformer
en degres ou en pourcentage est un choix d'ETALONNAGE, pas une propriete
du materiel : il est donc declare au registre, capteur par capteur, et
relu ici. Deux conversions existent :

  lm35      tension x 100. Le LM35 rend 10 mV par degre, c'est une
            equivalence physique, pas un reglage.

  lineaire  le rapport brut est etendu aux bornes `echelle` du capteur.
            C'est une convention d'affichage tant que la sonde n'a pas
            ete etalonnee pour de bon -- une photoresistance ne dit pas
            des lux, elle dit « plus clair » ou « moins clair ».

`gpiozero` n'est importe qu'a la premiere lecture : le poste de
developpement n'a pas de GPIO, et charger ce module ne doit pas l'y
empecher de tourner en MODE=faux.
"""

TENSION_PLEINE = 3.3

# Une voie ouverte par capteur, gardee entre deux lectures : gpiozero
# ouvre le peripherique SPI a la construction, et le rouvrir cinq fois
# par seconde finissait par echouer.
_voies = {}


def _voie(canal: int):
    if canal not in _voies:
        from gpiozero import MCP3004
        _voies[canal] = MCP3004(channel=canal)
    return _voies[canal]


def _lineaire(brut: float, params: dict) -> float:
    """Etend le rapport brut aux bornes declarees du capteur.

    `etalonnage` dit quelle portion de l'echelle electrique est utile :
    une sonde d'humidite ne descend jamais a zero volt, et prendre 0 a 1
    pour reference ecraserait toute la mesure dans un coin de la jauge.
    Une borne basse superieure a la haute inverse le sens -- c'est le cas
    des sondes resistives, qui montent en tension quand la terre seche.
    """
    etal = params.get("etalonnage", {})
    b0, b1 = etal.get("brut_bas", 0.0), etal.get("brut_haut", 1.0)
    v0, v1 = params["echelle"]["min"], params["echelle"]["max"]

    if b1 == b0:
        return float(v0)
    part = (brut - b0) / (b1 - b0)
    part = min(max(part, 0.0), 1.0)      # hors bornes : on plafonne
    return v0 + part * (v1 - v0)


CONVERSIONS = {
    "lm35": lambda brut, params: brut * TENSION_PLEINE * 100,
    "lineaire": _lineaire,
}


def lire(capteur_id, params):
    """Le rapport lu sur la voie, converti selon le registre."""
    brut = _voie(params["canal"]).value

    conversion = params.get("conversion", "lineaire")
    if conversion not in CONVERSIONS:
        raise ValueError(f"conversion inconnue : {conversion}")

    return round(CONVERSIONS[conversion](brut, params), 2)
