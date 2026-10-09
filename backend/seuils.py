"""Lecture des seuils appris dans le reseau.

Le reseau ne stocke aucun seuil : il juge. Mais si on fait varier une
grandeur en tenant les autres fixes, il existe un point ou son jugement
bascule -- de « trop bas » a « correct », puis de « correct » a « trop
haut ». Ces deux points SONT les seuils appris. On les lit en balayant,
plutot qu'en les demandant.

L'interet, par rapport a des valeurs ecrites dans capteurs.yaml : elles
dependent du contexte. Par temps chaud et lumineux, le reseau place le
seuil d'arrosage plus haut, parce que la terre seche plus vite.
"""

import numpy as np

import donnees
import reseau
from decision import GRANDEURS

# Finesse du balayage, en parts de l'etendue de la grandeur. 500 points
# suffisent : la frontiere est alors connue a un cinq-centieme pres.
PAS = 500


def _indices(grandeur: str) -> tuple[int, int, int]:
    """Colonne d'entree a balayer, et les deux sorties a lire."""
    entree = donnees.ENTREES.index(grandeur)
    bas = donnees.SORTIES.index(f"{grandeur}_bas")
    haut = donnees.SORTIES.index(f"{grandeur}_haut")
    return entree, bas, haut


def frontieres(poids: dict, bornes: np.ndarray,
               contexte: dict[str, float]) -> dict[str, dict]:
    """Les seuils de chaque grandeur, aux conditions donnees.

    `bas` ou `haut` valent None quand le reseau ne bascule jamais sur
    l'etendue de la grandeur -- soit qu'un tel etat n'existe pas, soit que
    le modele soit mal entraine. Dans les deux cas cela doit se voir,
    plutot que de s'inventer une valeur.
    """
    # Point de reference : les conditions du moment, completees par le
    # milieu de l'echelle pour ce qu'on ignore.
    base = np.array([[contexte.get(e, (bornes[i, 0] + bornes[i, 1]) / 2)
                      for i, e in enumerate(donnees.ENTREES)]], dtype=float)

    resultat: dict[str, dict] = {}
    for grandeur in GRANDEURS:
        # Le cumul d'eclairement ne se lit pas en balayant, et aucune
        # astuce n'y changera rien : il ne peut pas depasser le temps
        # ecoule depuis minuit. A neuf heures du matin, les douze heures
        # visees sont hors d'atteinte, le reseau juge donc « insuffisant »
        # sur toute l'etendue interrogeable, et il n'y a aucune bascule a
        # trouver. On a d'abord cru lire un seuil : c'etait le bord du
        # balayage, et il donnait « lumiere suffisante au-dela de 9 h ».
        #
        # Son seuil est donc pris la ou le reseau l'a appris -- le budget
        # du jour et sa tolerance. Deux constantes, et non une frontiere
        # qui se deplace avec la chaleur : c'est la seule grandeur du
        # projet dont le seuil « IA » ne respire pas, parce que c'est un
        # objectif et non un etat.
        if grandeur == "eclairement_jour":
            resultat[grandeur] = {
                "bas": donnees.CIBLE_LUMIERE_H,
                "haut": donnees.CIBLE_LUMIERE_H + donnees.MARGE_LUMIERE_H,
            }
            continue

        entree, i_bas, i_haut = _indices(grandeur)
        mini, maxi = float(bornes[entree, 0]), float(bornes[entree, 1])

        grille = np.linspace(mini, maxi, PAS)
        X = np.repeat(base, PAS, axis=0)
        X[:, entree] = grille

        juge = reseau.predire(poids, donnees.normaliser(X, bornes))
        demi = (maxi - mini) / (PAS - 1) / 2

        # Une bascule qui tombe au bord du balayage n'en est pas une : le
        # jugement vaut pour toute l'etendue interrogeable, et on ne sait
        # simplement pas ou il changerait. Rapporter ce bord comme un
        # seuil donnerait un chiffre faux -- a neuf heures du matin, on
        # lisait « lumiere suffisante au-dela de 9 h », qui n'est que la
        # limite du balayage.
        sous, sur = juge[:, i_bas], juge[:, i_haut]
        resultat[grandeur] = {
            "bas": round(float(grille[sous].max() + demi), 2)
                   if sous.any() and not sous[-1] else None,
            "haut": round(float(grille[sur].min() - demi), 2)
                    if sur.any() and not sur[0] else None,
        }
    return resultat
