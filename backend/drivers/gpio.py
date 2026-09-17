"""Driver des sorties tout ou rien : LED, buzzer, relais.

Une broche, deux etats. C'est le driver le plus simple du projet, et
c'est voulu : tout ce qui s'allume passe par ici, et ce qui differe d'un
actionneur a l'autre -- le numero de broche -- est declare au registre,
pas code ici.

`gpiozero` n'est importe qu'a la premiere ecriture : le poste de
developpement n'a pas de GPIO, et charger ce module ne doit pas l'y
empecher de tourner en MODE=faux.

Le retour n'est pas un echo de l'ordre recu mais l'etat RELU sur la
broche. Les deux coincident presque toujours ici -- une broche fait ce
qu'on lui dit -- mais c'est le contrat des drivers du projet, et le jour
ou un relais coincera, l'ecran le montrera au lieu de mentir.
"""

# Une sortie ouverte par actionneur, gardee entre deux commandes :
# reconstruire l'objet a chaque ordre relacherait la broche entre-temps,
# et la LED clignoterait a chaque commande identique.
_sorties = {}


def _sortie(broche: int):
    if broche not in _sorties:
        from gpiozero import DigitalOutputDevice
        # `DigitalOutputDevice` plutot que `LED` : le buzzer et un relais
        # ne sont pas des LED, et le nom du composant se lit dans le
        # registre, pas dans le type Python.
        _sorties[broche] = DigitalOutputDevice(broche)
    return _sorties[broche]


def appliquer(actionneur_id, valeur, params, lignes=None):
    """Met la broche au niveau demande et renvoie l'etat atteint.

    `lignes` ne concerne que l'afficheur ; on l'accepte et on l'ignore,
    pour que le service n'ait pas a savoir a qui il parle.
    """
    sortie = _sortie(params["broche"])
    if float(valeur) > 0:
        sortie.on()
    else:
        sortie.off()
    return float(sortie.value)
