"""Driver du telemetre a ultrasons HC-SR04.

Il ne mesure pas un niveau : il mesure une DISTANCE. Monte au-dessus du
reservoir et vise le liquide, alors une distance courte veut dire plein
et une distance longue veut dire vide -- l'inverse de ce qu'on affiche.

La conversion est donc un etalonnage, declare au registre : a quelle
distance le reservoir est plein, a quelle distance il est vide. Ces deux
nombres dependent de la hauteur a laquelle le capteur est visse, pas du
capteur : les ecrire ici les figerait pour un montage qui changera.

`gpiozero` lit le capteur dans son propre fil et lisse sur plusieurs
impulsions : une mesure aberrante -- une vaguelette, un echo parasite sur
la paroi -- ne fait pas sauter la valeur. La lecture est donc immediate.

Le fil d'echo sort du capteur en 5 V et doit passer par un pont diviseur
avant d'atteindre la broche, qui n'accepte que 3,3 V. C'est une affaire
de cablage, pas de code, mais elle se rappelle mal apres coup.
"""

import time

_capteurs = {}

# Dernier signalement d'une mesure hors etalonnage, par capteur.
_plainte = {}

# On ne se plaint qu'une fois par periode : sinon la trace serait emise
# deux fois par seconde.
SIGNALEMENT_S = 10.0


def _capteur(params):
    cle = (params["trigger"], params["echo"])
    if cle not in _capteurs:
        from gpiozero import DistanceSensor
        _capteurs[cle] = DistanceSensor(
            trigger=params["trigger"],
            echo=params["echo"],
            # Au-dela, le capteur rend sa portee maximale plutot qu'une
            # valeur : le declarer evite de prendre un silence pour une
            # mesure de plusieurs metres.
            max_distance=params.get("portee_m", 1.0),
        )
    return _capteurs[cle]


def lire(capteur_id, params):
    """Le remplissage en pourcentage, deduit de la distance mesuree."""
    distance_cm = _capteur(params).distance * 100

    etal = params.get("etalonnage", {})
    plein = etal.get("plein_cm", 5.0)      # liquide au ras du capteur
    vide = etal.get("vide_cm", 25.0)       # fond du reservoir

    if vide == plein:
        return 0.0

    # Plus c'est proche, plus c'est plein : la pente est negative.
    part = (vide - distance_cm) / (vide - plein)

    # Une valeur collee a 0 ou a 100 ne veut rien dire : ou le reservoir
    # est vraiment a fond, ou l'etalonnage ne correspond pas au montage.
    # On donne alors la distance brute, qui est la seule chose utile pour
    # corriger -- et une seule fois par periode, pour ne pas noyer le
    # journal.
    if not 0.0 < part < 1.0:
        maintenant = time.monotonic()
        if maintenant - _plainte.get(capteur_id, 0.0) > SIGNALEMENT_S:
            _plainte[capteur_id] = maintenant
            print(f"{capteur_id} : {distance_cm:.1f} cm mesures, hors de "
                  f"l'etalonnage {plein}-{vide} cm", flush=True)

    return round(min(max(part, 0.0), 1.0) * 100, 2)
