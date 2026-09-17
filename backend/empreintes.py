"""Les visages que la serre sait nommer.

Une empreinte, ce sont les 128 nombres que le modele tire d'un visage.
Reconnaitre quelqu'un, c'est mesurer la distance entre deux series de
nombres -- il n'y a rien a reapprendre, et ajouter une personne revient
a poser une ligne de plus dans la table.

Aucune photo n'est conservee. On ne remonte pas d'une empreinte au
visage dont elle vient, et la carte de la Pi ne porte donc pas une
galerie de portraits.
"""

import numpy as np

# Le modele rend toujours ce nombre de valeurs : le verifier a l'ecriture
# evite de decouvrir une empreinte tronquee au moment de comparer.
TAILLE = 128


def _vers_octets(empreinte: np.ndarray) -> bytes:
    """Serialisation brute, sans pickle : une empreinte relue ne doit
    jamais pouvoir executer du code."""
    plat = np.asarray(empreinte, dtype=np.float32).reshape(-1)
    if plat.size != TAILLE:
        raise ValueError(f"empreinte de {plat.size} nombres, {TAILLE} attendus")
    return plat.tobytes()


def _depuis_octets(brut: bytes) -> np.ndarray:
    # `frombuffer` rend une vue en LECTURE SEULE sur la memoire de la
    # base ; OpenCV veut un tableau a lui, d'ou la copie.
    return np.frombuffer(brut, dtype=np.float32).reshape(1, TAILLE).copy()


def lire(conn) -> list[tuple[str, np.ndarray]]:
    """Toutes les references, prêtes a comparer.

    Une liste et non un dictionnaire : une personne peut avoir plusieurs
    empreintes -- de face, de trois quarts -- et c'est la meilleure des
    ressemblances qui decide.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT nom, empreinte FROM visages ORDER BY nom, id")
        return [(nom, _depuis_octets(brut)) for nom, brut in cur.fetchall()]


def enregistrer(conn, nom: str, empreinte: np.ndarray, origine: str) -> None:
    """Ajoute une reference. Les precedentes restent : deux prises de vue
    d'une meme personne valent mieux qu'une."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO visages (nom, empreinte, origine) VALUES (%s, %s, %s)",
            (nom, _vers_octets(empreinte), origine),
        )


def retirer(conn, nom: str) -> int:
    """Oublie quelqu'un, et rend le nombre de references effacees."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM visages WHERE nom = %s", (nom,))
        return cur.rowcount


def inventaire(conn) -> list[tuple[str, int]]:
    """Qui la serre connait, et avec combien de references chacun."""
    with conn.cursor() as cur:
        cur.execute("SELECT nom, count(*) FROM visages GROUP BY nom ORDER BY nom")
        return cur.fetchall()
