"""Lecture des seuils appris dans le reseau.

Le reseau ne produit pas de seuils : il produit une action. Mais si on
fait varier l'humidite en tenant les autres entrees fixes, il existe un
point ou sa reponse bascule de « arroser » a « ne rien faire ». Ce point
EST le seuil qu'il a appris. On le lit donc en balayant, plutot qu'en le
demandant.

L'interet, par rapport a deux constantes ecrites dans capteurs.yaml :
ces seuils DEPENDENT des autres mesures. Par temps chaud et lumineux, le
reseau declenche l'arrosage plus tot, parce que la terre seche plus vite.
"""

import numpy as np

import donnees
import reseau

# Reserve supposee pleine pour le balayage : sous le seuil de securite,
# le reseau n'arrose jamais et aucune frontiere basse n'existerait.
RESERVE_AFFICHAGE = 80.0

PAS = 0.2   # en points d'humidite


def frontieres(poids: dict, bornes: np.ndarray, temperature: float,
               luminosite: float, eau: float = RESERVE_AFFICHAGE) -> dict:
    """Les deux bascules, en pourcentage d'humidite du sol.

    `bas` : au-dessous, le reseau arrose. `haut` : au-dessus, il ventile.
    L'un ou l'autre vaut None si le reseau ne bascule jamais -- ce qui
    signale un modele mal entraine, et doit se voir plutot que de
    s'inventer une valeur.
    """
    grille = np.arange(0.0, 100.0 + PAS, PAS)
    X = np.column_stack([
        grille,
        np.full_like(grille, temperature),
        np.full_like(grille, luminosite),
        np.full_like(grille, eau),
    ])
    classes = reseau.predire(poids, donnees.normaliser(X, bornes))

    arrose = grille[classes == donnees.ARROSER]
    ventile = grille[classes == donnees.VENTILER]

    return {
        # Derniere humidite ou il arrose encore : la frontiere est juste
        # au-dessus.
        "bas": round(float(arrose.max() + PAS / 2), 1) if len(arrose) else None,
        "haut": round(float(ventile.min() - PAS / 2), 1) if len(ventile) else None,
    }
