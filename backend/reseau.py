"""Un perceptron multicouche, ecrit a la main.

NumPy et rien d'autre : ni framework, ni modele telecharge. Ce module ne
connait ni la base, ni MQTT, ni les capteurs -- il prend des tableaux de
nombres et en rend d'autres. C'est ce qui permet de l'entrainer et de le
verifier sans lancer la moindre infrastructure.

Architecture : une couche cachee a tangente hyperbolique, une sortie
softmax, perte d'entropie croisee. Assez pour apprendre des frontieres
courbes -- un seuil qui se deplace avec la chaleur et la lumiere -- et
assez petit pour tourner sur une Raspberry Pi sans y penser.
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


def _softmax(z: np.ndarray) -> np.ndarray:
    # On retranche le maximum avant l'exponentielle : mathematiquement
    # sans effet, mais cela evite un depassement de capacite.
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def avant(p: Poids, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Propagation avant. Renvoie les probabilites et l'activation cachee,
    cette derniere etant necessaire a la retropropagation."""
    cache = np.tanh(X @ p["W1"] + p["b1"])
    return _softmax(cache @ p["W2"] + p["b2"]), cache


def perte(probas: np.ndarray, y: np.ndarray) -> float:
    """Entropie croisee : -log de la probabilite donnee a la bonne classe.

    Le plancher evite un logarithme de zero quand le reseau est tres sur
    de lui et se trompe.
    """
    n = len(y)
    return float(-np.log(np.maximum(probas[np.arange(n), y], 1e-12)).mean())


def arriere(p: Poids, X: np.ndarray, cache: np.ndarray,
            probas: np.ndarray, y: np.ndarray) -> Poids:
    """Retropropagation.

    Le gradient de l'entropie croisee composee avec softmax se simplifie
    en (probabilites - verite) : c'est precisement pour cette raison
    qu'on associe toujours ces deux-la.
    """
    n = len(y)
    dz2 = probas.copy()
    dz2[np.arange(n), y] -= 1
    dz2 /= n

    dz1 = (dz2 @ p["W2"].T) * (1 - cache**2)   # derivee de tanh
    return {
        "W2": cache.T @ dz2, "b2": dz2.sum(axis=0),
        "W1": X.T @ dz1, "b1": dz1.sum(axis=0),
    }


def entrainer(X: np.ndarray, y: np.ndarray, *, n_caches: int = 8,
              taux: float = 0.5, epoques: int = 3000, graine: int = 0,
              trace_tous: int = 300) -> tuple[Poids, list[dict]]:
    """Descente de gradient sur le lot entier.

    Le jeu tient en memoire et reste petit : inutile de le decouper en
    mini-lots, le gradient exact coute moins cher qu'une approximation
    bruitee ici.
    """
    p = initialiser(X.shape[1], n_caches, int(y.max()) + 1, graine)
    historique = []

    for epoque in range(epoques + 1):
        probas, cache = avant(p, X)
        if epoque % trace_tous == 0:
            historique.append({
                "epoque": epoque,
                "perte": round(perte(probas, y), 4),
                "exactitude": round(float((probas.argmax(1) == y).mean()), 4),
            })
        if epoque == epoques:
            break
        g = arriere(p, X, cache, probas, y)
        for cle in p:
            p[cle] -= taux * g[cle]

    return p, historique


def predire(p: Poids, X: np.ndarray) -> np.ndarray:
    """La classe la plus probable pour chaque ligne."""
    return avant(p, X)[0].argmax(axis=1)


def exactitude(p: Poids, X: np.ndarray, y: np.ndarray) -> float:
    return float((predire(p, X) == y).mean())
