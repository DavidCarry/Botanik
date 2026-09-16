"""Jeu de donnees d'entrainement, et les regles qui l'etiquettent.

Le sujet autorise explicitement de creer son propre jeu. C'est ce qu'on
fait, et il faut l'assumer : le reseau apprend a reproduire les regles
ecrites ici. Ce qu'on demontre n'est donc pas qu'il a decouvert
l'agronomie, mais qu'il a APPRIS -- sur des exemples qu'il n'a jamais vus.

Aucune base publique ne pouvait fournir ces etiquettes : elles dependent
de CETTE pompe, de CETTE bassine et de la calibration de CETTE sonde
capacitive, dont les pourcentages ne sont comparables a ceux d'aucun
autre montage.

Ce que le reseau apprend, ce sont des JUGEMENTS -- « trop bas ? trop
haut ? » pour chaque grandeur -- et non des commandes. Les actionneurs
en decoulent par une regle explicite, dans decision.py. Ce partage donne
un seuil lisible meme aux grandeurs sur lesquelles on ne peut pas agir,
comme la temperature.
"""

import numpy as np

import registre
from decision import GRANDEURS

# L'ordre compte : c'est celui des colonnes que le reseau recevra, et il
# doit etre le meme a l'entrainement et a l'inference.
#
# Les deux dernieres entrees ne sont pas des mesures de capteur :
#   eclairement_jour  heures passees sous une lumiere suffisante depuis minuit
#   heure             l'heure qu'il est, entre 0 et 24
# Sans elles, le budget quotidien de lumiere serait indecidable : savoir
# qu'il fait sombre ne dit pas s'il est trop tard pour rattraper.
ENTREES = [
    "humidite_sol_a", "temperature_air", "luminosite", "niveau_eau",
    "eclairement_jour", "heure",
]

# Deux sorties par grandeur jugee : sous le seuil bas, au-dessus du haut.
SORTIES = [f"{g}_{cote}" for g in GRANDEURS for cote in ("bas", "haut")]

# Bornes des entrees qui ne viennent pas du registre des capteurs.
HORS_REGISTRE = {"eclairement_jour": (0.0, 24.0), "heure": (0.0, 24.0)}

# Duree d'eclairement visee par jour, et tolerance au-dela de laquelle
# on considere qu'il y en a eu trop. Une plante a besoin de nuit autant
# que de jour.
CIBLE_LUMIERE_H = 12.0
MARGE_LUMIERE_H = 1.0

# Plage horaire pendant laquelle il est raisonnable d'allumer. Rattraper
# un retard de lumiere a trois heures du matin desorganiserait la plante.
FENETRE_ECLAIRAGE = (6.0, 22.0)

# Seuil a partir duquel l'eclairement compte comme « suffisant ».
LUX_UTILE = 3000.0


def bornes() -> np.ndarray:
    """Echelle physique de chaque entree.

    Normaliser par ces bornes plutot que par la moyenne du jeu : elles ne
    dependent pas de l'echantillon, donc l'inference n'a pas besoin de
    rejouer des statistiques d'entrainement pour interpreter une mesure.
    """
    connus = {c["id"]: c for c in registre.capteurs_actifs()}
    lignes = []
    for e in ENTREES:
        if e in HORS_REGISTRE:
            lignes.append(HORS_REGISTRE[e])
        elif e in connus:
            lignes.append((connus[e]["echelle"]["min"], connus[e]["echelle"]["max"]))
        else:
            raise ValueError(f"capteur inactif ou absent du registre : {e}")
    return np.array(lignes, dtype=float)


def normaliser(X: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Ramene chaque colonne entre 0 et 1.

    Sans cela, la luminosite (jusqu'a 12 000) ecraserait l'humidite
    (0 a 100) : le reseau ne verrait qu'elle.
    """
    return (X - b[:, 0]) / (b[:, 1] - b[:, 0])


def _demande(temperature: np.ndarray, luminosite: np.ndarray) -> np.ndarray:
    """Intensite de l'evaporation, de 0 a 1.

    Il fait chaud et clair : la terre seche vite, il faut arroser plus
    tot. C'est ce terme qui rend les seuils d'humidite mobiles -- et
    c'est tout l'interet d'un reseau plutot que de deux constantes.
    """
    t = np.clip((temperature - 10) / 25, 0, 1)
    l = np.clip(luminosite / 9000, 0, 1)
    return 0.6 * t + 0.4 * l


def etiqueter(X: np.ndarray) -> np.ndarray:
    """Les regles agronomiques, une colonne par jugement."""
    humidite, temperature, luminosite, eau, cumul, heure = X.T
    d = _demande(temperature, luminosite)
    debut, fin = FENETRE_ECLAIRAGE

    return np.column_stack([
        # Humidite du sol : seuils mobiles, ils suivent l'evaporation.
        humidite < 44 + 10 * d,
        humidite > 78 - 6 * d,
        # Temperature : plage de germination de la lentille. Rien ne peut
        # agir dessus, mais la juger permet de l'afficher et d'alerter.
        temperature < 18,
        temperature > 24,
        # Luminosite instantanee : trop faible pour compter, ou assez
        # forte pour bruler les jeunes pousses.
        luminosite < LUX_UTILE,
        luminosite > 11000,
        # Reserve d'eau : a remplir, ou au bord du debordement.
        eau < 20,
        eau > 95,
        # Budget de lumiere du jour, fenetre horaire comprise.
        (cumul < CIBLE_LUMIERE_H) & (heure >= debut) & (heure < fin),
        cumul > CIBLE_LUMIERE_H + MARGE_LUMIERE_H,
    ]).astype(float)


def generer(n: int = 8000, graine: int = 0) -> tuple[np.ndarray, np.ndarray]:
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
    n_uniforme = n - n_cycle

    heure_c = r.uniform(0, 24, n_cycle)
    cycle = np.sin((heure_c - 6) / 24 * 2 * np.pi)
    reel = np.column_stack([
        r.uniform(0, 100, n_cycle),
        21 + 6 * cycle + r.normal(0, 3, n_cycle),
        np.maximum(0, 9000 * cycle + r.normal(0, 400, n_cycle)),
        r.uniform(0, 100, n_cycle),
        np.zeros(n_cycle),          # rempli plus bas
        heure_c,
    ])

    heure_u = r.uniform(0, 24, n_uniforme)
    uniforme = np.column_stack([
        r.uniform(0, 100, n_uniforme),
        r.uniform(10, 35, n_uniforme),
        r.uniform(0, 12000, n_uniforme),
        r.uniform(0, 100, n_uniforme),
        np.zeros(n_uniforme),
        heure_u,
    ])

    X = np.vstack([reel, uniforme])

    # Le cumul du jour ne peut pas depasser le temps ecoule depuis minuit :
    # tirer les deux independamment produirait des situations impossibles,
    # et le reseau apprendrait sur des exemples qui n'arrivent jamais.
    heure = X[:, ENTREES.index("heure")]
    X[:, ENTREES.index("eclairement_jour")] = r.uniform(0, 1, len(X)) * np.minimum(heure, 16.0)

    # Les bornes physiques restent des bornes : une sonde ne renvoie pas
    # -3 % d'humidite.
    b = bornes()
    X = np.clip(X, b[:, 0], b[:, 1])

    r.shuffle(X)
    return X, etiqueter(X)


def separer(X: np.ndarray, Y: np.ndarray, part_test: float = 0.2,
            graine: int = 0):
    """Apprentissage / test. Le sujet exige d'evaluer l'inference sur des
    exemples que le reseau n'a jamais vus."""
    r = np.random.default_rng(graine)
    ordre = r.permutation(len(X))
    coupe = int(len(X) * (1 - part_test))
    a, t = ordre[:coupe], ordre[coupe:]
    return X[a], Y[a], X[t], Y[t]
