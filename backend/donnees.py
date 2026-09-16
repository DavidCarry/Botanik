"""Jeu de donnees d'entrainement, et les regles qui l'etiquettent.

Le sujet autorise explicitement de creer son propre jeu. C'est ce qu'on
fait, et il faut l'assumer : le reseau apprend a reproduire les regles
ecrites ici. Ce qu'on demontre n'est donc pas qu'il a decouvert
l'agronomie, mais qu'il a APPRIS -- sur des exemples qu'il n'a jamais vus.

Aucune base publique ne pouvait fournir ces etiquettes : la decision
d'arroser depend de CETTE pompe, de CETTE bassine et de la calibration de
CETTE sonde capacitive, dont les pourcentages ne sont comparables a ceux
d'aucun autre montage.
"""

import numpy as np

import registre

# L'ordre compte : c'est celui des colonnes que le reseau recevra, et il
# doit etre le meme a l'entrainement et a l'inference.
ENTREES = ["humidite_sol_a", "temperature_air", "luminosite", "niveau_eau"]

ACTIONS = ["rien", "arroser", "ventiler"]
RIEN, ARROSER, VENTILER = 0, 1, 2

# Sous ce niveau, la bassine est consideree vide : faire tourner la pompe
# a sec l'abime. La regle est enseignee au reseau ET conservee en dur dans
# le service -- un reseau se trompe parfois, une pompe grillee est
# definitive.
RESERVE_MINIMALE = 15.0


def bornes() -> np.ndarray:
    """Echelle physique de chaque entree, prise dans le registre.

    Normaliser par ces bornes plutot que par la moyenne du jeu : elles ne
    dependent pas de l'echantillon, donc l'inference n'a pas besoin de
    rejouer des statistiques d'entrainement pour interpreter une mesure.
    """
    connus = {c["id"]: c for c in registre.capteurs_actifs()}
    manquants = [e for e in ENTREES if e not in connus]
    if manquants:
        raise ValueError(f"capteurs inactifs ou absents du registre : {manquants}")
    return np.array([[connus[e]["echelle"]["min"], connus[e]["echelle"]["max"]]
                     for e in ENTREES], dtype=float)


def normaliser(X: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Ramene chaque colonne entre 0 et 1.

    Sans cela, la luminosite (jusqu'a 12 000) ecraserait l'humidite
    (0 a 100) : le reseau ne verrait qu'elle.
    """
    return (X - b[:, 0]) / (b[:, 1] - b[:, 0])


def _demande(temperature: np.ndarray, luminosite: np.ndarray) -> np.ndarray:
    """Intensite de l'evaporation, de 0 a 1.

    Il fait chaud et clair : la terre seche vite, il faut arroser plus
    tot. C'est ce terme qui rend les seuils mobiles -- et c'est tout
    l'interet d'un reseau plutot que de deux constantes.
    """
    t = np.clip((temperature - 10) / 25, 0, 1)
    l = np.clip(luminosite / 9000, 0, 1)
    return 0.6 * t + 0.4 * l


def etiqueter(X: np.ndarray) -> np.ndarray:
    """Les regles agronomiques. Germination de la lentille : la terre doit
    rester humide sans etre detrempee, sous peine de pourrissement."""
    humidite, temperature, luminosite, eau = X.T
    d = _demande(temperature, luminosite)

    seuil_bas = 44 + 10 * d     # sous ce taux, il faut arroser
    seuil_haut = 78 - 6 * d     # au-dessus, il faut assecher

    y = np.full(len(X), RIEN, dtype=int)
    y[humidite < seuil_bas] = ARROSER
    y[humidite > seuil_haut] = VENTILER
    # La reserve prime sur tout le reste : pas d'eau, pas d'arrosage.
    y[(y == ARROSER) & (eau < RESERVE_MINIMALE)] = RIEN
    return y


def generer(n: int = 6000, graine: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Tire des conditions plausibles et les etiquette.

    Deux tiers suivent un cycle jour/nuit -- temperature et luminosite y
    sont correlees, comme dans la realite et comme dans le simulateur.
    Le dernier tiers est tire uniformement sur toute l'etendue : sans lui,
    le reseau n'aurait jamais vu de canicule nocturne, et se comporterait
    n'importe comment dans les coins ou on l'interrogera pour tracer ses
    frontieres.
    """
    r = np.random.default_rng(graine)
    n_cycle = int(n * 2 / 3)

    heure = r.uniform(0, 24, n_cycle)
    cycle = np.sin((heure - 6) / 24 * 2 * np.pi)
    reel = np.column_stack([
        r.uniform(0, 100, n_cycle),                                  # humidite
        21 + 6 * cycle + r.normal(0, 3, n_cycle),                    # temperature
        np.maximum(0, 9000 * cycle + r.normal(0, 400, n_cycle)),     # luminosite
        r.uniform(0, 100, n_cycle),                                  # niveau d'eau
    ])

    n_uniforme = n - n_cycle
    uniforme = np.column_stack([
        r.uniform(0, 100, n_uniforme),
        r.uniform(10, 35, n_uniforme),
        r.uniform(0, 12000, n_uniforme),
        r.uniform(0, 100, n_uniforme),
    ])

    X = np.vstack([reel, uniforme])
    # Les bornes physiques restent des bornes : une sonde ne renvoie pas
    # -3 % d'humidite.
    b = bornes()
    X = np.clip(X, b[:, 0], b[:, 1])

    r.shuffle(X)
    return X, etiqueter(X)


def separer(X: np.ndarray, y: np.ndarray, part_test: float = 0.2,
            graine: int = 0):
    """Apprentissage / test. Le sujet exige d'evaluer l'inference sur des
    exemples que le reseau n'a jamais vus."""
    r = np.random.default_rng(graine)
    ordre = r.permutation(len(X))
    coupe = int(len(X) * (1 - part_test))
    a, t = ordre[:coupe], ordre[coupe:]
    return X[a], y[a], X[t], y[t]
