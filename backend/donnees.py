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
#
# Tirees de leur echelle declaree, et non recopiees : c'est la meme
# echelle qui borne le reseau ici et qui graduera le champ de saisie
# dans les reglages.
HORS_REGISTRE = {
    grandeur: (float(d["echelle"]["min"]), float(d["echelle"]["max"]))
    for grandeur, d in registre.HORS_CAPTEUR.items()
}

# Duree d'eclairement visee par jour, et tolerance au-dela de laquelle
# on considere qu'il y en a eu trop. Une plante a besoin de nuit autant
# que de jour.
CIBLE_LUMIERE_H = 12.0
MARGE_LUMIERE_H = 1.0

# Plage horaire pendant laquelle il est raisonnable d'allumer. Rattraper
# un retard de lumiere a trois heures du matin desorganiserait la plante.
FENETRE_ECLAIRAGE = (6.0, 22.0)

# Seuil a partir duquel l'eclairement compte comme « suffisant », dans
# l'unite du capteur -- un pourcentage de clarte, pas des lux.
#
# Defini ICI et nulle part ailleurs : le calcul du budget quotidien s'en
# sert aussi, et deux constantes qui doivent rester egales finissent
# toujours par diverger.
ECLAIREMENT_UTILE = 25.0

# Au-dela, la lumiere brule les jeunes pousses.
ECLAIREMENT_EXCESSIF = 92.0


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
    l = np.clip(luminosite / 75, 0, 1)
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
        luminosite < ECLAIREMENT_UTILE,
        luminosite > ECLAIREMENT_EXCESSIF,
        # Reserve d'eau : a remplir, ou au bord du debordement.
        eau < 20,
        eau > 95,
        # Budget de lumiere du jour, fenetre horaire comprise.
        (cumul < CIBLE_LUMIERE_H) & (heure >= debut) & (heure < fin),
        cumul > CIBLE_LUMIERE_H + MARGE_LUMIERE_H,
    ]).astype(float)


def _bords(r, n: int, b: np.ndarray) -> np.ndarray:
    """Un lot concentre au voisinage des bords d'echelle.

    Sans lui, une frontiere posee tout au bord reste sous-apprise : la
    zone « trop de lumiere » ne couvre que le douzieme de l'echelle, donc
    2 % d'un tirage uniforme. Le reseau n'y voyait pas assez d'exemples
    pour etre sur de lui -- sa probabilite atteignait peine 0,53 au bout
    de l'echelle, et le seuil devenait illisible selon les conditions.

    Chaque exemple de ce lot pousse UNE grandeur tiree au sort dans le
    cinquieme haut ou bas de son echelle, les autres restant uniformes :
    les deux cotes de chaque bascule sont ainsi peuples.
    """
    X = np.column_stack([r.uniform(b[i, 0], b[i, 1], n) for i in range(len(ENTREES))])

    mesurees = len(ENTREES) - len(HORS_REGISTRE)
    axe = r.integers(0, mesurees, n)
    haut = r.random(n) < 0.5
    part = r.random(n) * 0.2

    for i in range(n):
        j = axe[i]
        mini, maxi = b[j]
        etendue = maxi - mini
        X[i, j] = maxi - part[i] * etendue if haut[i] else mini + part[i] * etendue
    return X


def generer(n: int = 9000, graine: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Tire des conditions plausibles et les etiquette.

    Trois lots, chacun pour une raison :

    - la moitie suit un cycle jour/nuit, temperature et luminosite
      correlees comme dans la realite et comme dans le simulateur ;
    - un quart est tire uniformement sur toute l'etendue, sans quoi le
      reseau n'aurait jamais vu de canicule nocturne et repondrait
      n'importe quoi dans les coins ou on l'interroge pour tracer ses
      frontieres ;
    - un quart se presse contre les bords, pour que les bascules situees
      en bout d'echelle soient apprises aussi fermement que les autres.
    """
    r = np.random.default_rng(graine)
    b = bornes()
    n_cycle = n // 2
    n_bords = n // 4
    n_uniforme = n - n_cycle - n_bords

    # L'etendue de la luminosite se lit au registre plutot que de
    # s'ecrire en clair : le jour ou l'echelle du capteur change -- des
    # lux vers un pourcentage, par exemple -- le jeu de donnees suit tout
    # seul. Ecrite en dur, elle produisait un ciel perpetuellement
    # aveuglant et un jugement « lumiere excessive » toujours vrai.
    lum_min, lum_max = b[ENTREES.index("luminosite")]
    lum_etendue = lum_max - lum_min

    heure_c = r.uniform(0, 24, n_cycle)
    cycle = np.sin((heure_c - 6) / 24 * 2 * np.pi)
    reel = np.column_stack([
        r.uniform(0, 100, n_cycle),
        21 + 6 * cycle + r.normal(0, 3, n_cycle),
        np.maximum(lum_min,
                   0.75 * lum_etendue * cycle
                   + r.normal(0, 0.033 * lum_etendue, n_cycle)),
        r.uniform(0, 100, n_cycle),
        np.zeros(n_cycle),          # rempli plus bas
        heure_c,
    ])

    # Meme raison : le lot uniforme couvre l'etendue declaree de chaque
    # entree, quelle qu'elle soit.
    uniforme = np.column_stack(
        [r.uniform(b[j, 0], b[j, 1], n_uniforme) for j in range(len(ENTREES))]
    )

    X = np.vstack([reel, uniforme, _bords(r, n_bords, b)])

    # Le cumul du jour ne peut pas depasser le temps ecoule depuis minuit :
    # tirer les deux independamment produirait des situations impossibles,
    # et le reseau apprendrait sur des exemples qui n'arrivent jamais.
    i_cumul, i_heure = ENTREES.index("eclairement_jour"), ENTREES.index("heure")
    heure = X[:, i_heure]
    plafond = np.minimum(heure, 16.0)
    X[:, i_cumul] = r.uniform(0, 1, len(X)) * plafond

    # Un cinquieme des exemples se place autour de la cible quotidienne,
    # la seule bascule qui compte pour la lumiere. Un tirage uniforme ne
    # place presque personne entre 12 et 13 heures.
    proche = (r.random(len(X)) < 0.2) & (plafond > CIBLE_LUMIERE_H)
    X[proche, i_cumul] = np.clip(
        CIBLE_LUMIERE_H + r.uniform(-2, 2.5, proche.sum()),
        0, plafond[proche],
    )

    # Les bornes physiques restent des bornes : une sonde ne renvoie pas
    # -3 % d'humidite.
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
