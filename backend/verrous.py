"""Qui, du modele ou de la main, commande en ce moment.

Une commande manuelle pose un verrou : le modele n'a plus le droit de
toucher a cet actionneur pendant un temps. La duree vit dans decision.py,
avec les autres regles du domaine.

Le verrou se DEDUIT du journal des commandes plutot que de s'entretenir
en memoire. Deux raisons : le cerveau et l'API doivent voir exactement la
meme chose -- sinon l'ecran annoncerait un verrou que le modele
ignorerait -- et un service qui redemarre retrouve les verrous en cours
au lieu de rendre la main d'un coup.
"""

from datetime import datetime, timedelta, timezone

from decision import VERROU_MANUEL_S

REQUETE = """
    SELECT actionneur, max(ts)
    FROM commandes
    WHERE source = 'manuel' AND ts > now() - %s * INTERVAL '1 second'
    GROUP BY actionneur
"""


def actifs(conn) -> dict[str, datetime]:
    """Les actionneurs sous verrou, et l'instant ou chacun se libere."""
    with conn.cursor() as cur:
        cur.execute(REQUETE, (VERROU_MANUEL_S,))
        lignes = cur.fetchall()
    return {
        actionneur: derniere + timedelta(seconds=VERROU_MANUEL_S)
        for actionneur, derniere in lignes
    }


def restant(fin: datetime | None) -> int:
    """Secondes avant liberation, ou 0. Jamais negatif : un verrou expire
    n'existe plus, il ne compte pas a rebours dans l'autre sens."""
    if fin is None:
        return 0
    return max(0, round((fin - datetime.now(timezone.utc)).total_seconds()))
