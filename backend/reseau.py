"""Un perceptron multicouche, ecrit a la main.

NumPy et rien d'autre : ni framework, ni modele telecharge. Ce module ne
connait ni la base, ni MQTT, ni les capteurs -- il prend des tableaux de
nombres et en rend d'autres. C'est ce qui permet de l'entrainer et de le
verifier sans lancer la moindre infrastructure.

Architecture : une couche cachee a tangente hyperbolique, une couche de
sortie a SIGMOIDES INDEPENDANTES, perte d'entropie croisee binaire.

Le choix des sigmoides plutot que d'un softmax est structurant : les
jugements ne s'excluent pas. La terre peut etre trop seche pendant que la
reserve est trop basse et que la journee manque de lumiere. Un softmax
aurait force le reseau a n'en retenir qu'un.
"""

import numpy as np

# Les poids sont un simple dictionnaire de tableaux : facile a serialiser,
# facile a inspecter, aucune classe a reconstruire pour recharger.
Poids = dict[str, np.ndarray]


def initialiser(n_entrees: int, n_caches: int, n_sorties: int,
                graine: int = 0) -> Poids:
    """Initialisation de Xavier.

    Des poids tires a variance 1/n gardent le signal a la meme echelle
    d'une couche a l'autre. Trop grands, la tangente hyperbolique sature
    et le gradient disparait ; trop petits, le reseau met une eternite a
    demarrer.
    """
    r = np.random.default_rng(graine)
    return {
        "W1": r.normal(0, np.sqrt(1 / n_entrees), (n_entrees, n_caches)),
        "b1": np.zeros(n_caches),
        "W2": r.normal(0, np.sqrt(1 / n_caches), (n_caches, n_sorties)),
        "b2": np.zeros(n_sorties),
    }


def _sigmoide(z: np.ndarray) -> np.ndarray:
    # Forme stable : l'exponentielle n'est jamais appliquee a un grand
    # positif, ce qui eviterait un depassement de capacite.
    return np.where(z >= 0, 1 / (1 + np.exp(-np.abs(z))),
                    np.exp(-np.abs(z)) / (1 + np.exp(-np.abs(z))))


def avant(p: Poids, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Propagation avant. Renvoie les probabilites et l'activation cachee,
    cette derniere etant necessaire a la retropropagation."""
    cache = np.tanh(X @ p["W1"] + p["b1"])
    return _sigmoide(cache @ p["W2"] + p["b2"]), cache


def perte(probas: np.ndarray, Y: np.ndarray) -> float:
    """Entropie croisee binaire, moyennee sur les exemples et les sorties.

    Le plancher evite un logarithme de zero quand le reseau est tres sur
    de lui et se trompe.
    """
    q = np.clip(probas, 1e-12, 1 - 1e-12)
    return float(-(Y * np.log(q) + (1 - Y) * np.log(1 - q)).mean())


def arriere(p: Poids, X: np.ndarray, cache: np.ndarray,
            probas: np.ndarray, Y: np.ndarray) -> Poids:
    """Retropropagation.

    Le gradient de l'entropie croisee binaire composee avec la sigmoide
    se simplifie en (probabilites - verite) : c'est precisement pour
    cette raison qu'on associe toujours ces deux-la.
    """
    dz2 = (probas - Y) / (Y.shape[0] * Y.shape[1])
    dz1 = (dz2 @ p["W2"].T) * (1 - cache**2)   # derivee de tanh
    return {
        "W2": cache.T @ dz2, "b2": dz2.sum(axis=0),
        "W1": X.T @ dz1, "b1": dz1.sum(axis=0),
    }


def entrainer(X: np.ndarray, Y: np.ndarray, *, n_caches: int = 12,
              taux: float = 1.5, epoques: int = 6000, graine: int = 0,
              trace_tous: int = 500) -> tuple[Poids, list[dict]]:
    """Descente de gradient sur le lot entier.

    Le jeu tient en memoire et reste petit : inutile de le decouper en
    mini-lots, le gradient exact coute moins cher qu'une approximation
    bruitee ici.
    """
    p = initialiser(X.shape[1], n_caches, Y.shape[1], graine)
    historique = []

    for epoque in range(epoques + 1):
        probas, cache = avant(p, X)
        if epoque % trace_tous == 0:
            historique.append({
                "epoque": epoque,
                "perte": round(perte(probas, Y), 4),
                "exactitude": round(exactitude(p, X, Y), 4),
            })
        if epoque == epoques:
            break
        g = arriere(p, X, cache, probas, Y)
        for cle in p:
            p[cle] -= taux * g[cle]

    return p, historique


def predire(p: Poids, X: np.ndarray) -> np.ndarray:
    """Chaque sortie, vraie ou fausse, independamment des autres."""
    return avant(p, X)[0] >= 0.5


def exactitude(p: Poids, X: np.ndarray, Y: np.ndarray) -> float:
    """Part des jugements corrects, toutes sorties confondues."""
    return float((predire(p, X) == (Y >= 0.5)).mean())


def exactitude_complete(p: Poids, X: np.ndarray, Y: np.ndarray) -> float:
    """Part des exemples ou TOUS les jugements sont corrects a la fois.

    Plus severe, et plus proche de ce qui compte : une situation n'est
    bien lue que si le reseau ne se trompe sur aucune grandeur.
    """
    return float((predire(p, X) == (Y >= 0.5)).all(axis=1).mean())
