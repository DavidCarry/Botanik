"""Rangement des poids du reseau en base de donnees.

Le sujet exige que les poids soient « transferables depuis une base de
donnees » -- c'est l'exigence openweight. La table `modeles` les porte
donc, avec de quoi les relire : architecture, ordre des entrees, bornes
de normalisation et metriques obtenues.

Sans ces metadonnees, les poids seuls ne servent a rien : on ne saurait
plus dans quel ordre presenter les mesures, ni sur quelle echelle les
ramener.
"""

import io
import json

import numpy as np
from psycopg.types.json import Jsonb

# Le modele ne produit plus des seuils d'humidite mais des jugements sur
# toutes les grandeurs : son nom le dit.
NOM = "jugements-serre"


def _vers_octets(poids: dict) -> bytes:
    """Serialisation NumPy native, sans pickle : un fichier de poids ne
    doit jamais pouvoir executer du code a la relecture."""
    tampon = io.BytesIO()
    np.savez(tampon, **poids)
    return tampon.getvalue()


def _depuis_octets(brut: bytes) -> dict:
    with np.load(io.BytesIO(brut), allow_pickle=False) as archive:
        return {cle: archive[cle] for cle in archive.files}


def enregistrer(conn, poids: dict, metadonnees: dict, version: str) -> None:
    """Ajoute une version. Les anciennes restent : pouvoir revenir au
    modele d'hier vaut mieux que d'ecraser celui qui marchait."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO modeles (nom, version, poids, metadonnees) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (nom, version) DO UPDATE "
            "SET poids = EXCLUDED.poids, metadonnees = EXCLUDED.metadonnees",
            (NOM, version, _vers_octets(poids), Jsonb(metadonnees)),
        )


def charger(conn) -> tuple[dict, dict, str] | None:
    """La version la plus recente, ou None si aucune n'a ete entrainee."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT poids, metadonnees, version FROM modeles "
            "WHERE nom = %s ORDER BY cree_le DESC LIMIT 1",
            (NOM,),
        )
        ligne = cur.fetchone()
    if not ligne:
        return None
    brut, meta, version = ligne
    return _depuis_octets(bytes(brut)), meta, version


def exporter(poids: dict, metadonnees: dict, chemin) -> None:
    """Sortie sur fichier, pour inspecter un modele hors de la base."""
    np.savez(chemin, **poids)
    with open(str(chemin) + ".json", "w", encoding="utf-8") as f:
        json.dump(metadonnees, f, indent=2, ensure_ascii=False)
