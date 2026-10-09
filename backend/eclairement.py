"""Le temps passe sous une lumiere suffisante depuis minuit.

Ni une mesure de capteur, ni un etat a maintenir quelque part : un cumul
qui se recalcule depuis l'historique deja archive. La base sait a quelle
heure la luminosite a franchi le seuil utile et pendant combien de temps
elle s'y est tenue -- il suffit de le lui demander.

L'avantage sur un compteur entretenu en memoire : un service qui
redemarre a midi retrouve immediatement le bon cumul, au lieu de repartir
de zero et de rallumer la lampe pour rien.

Et comme le cumul est RECALCULE et non accumule, changer le seuil de
lumiere utile rejoue tout l'historique du jour : le chiffre devient juste
immediatement, au lieu de melanger deux definitions de « eclaire » selon
l'heure a laquelle on a change d'avis.
"""

from config import ARCHIVAGE_S
from donnees import ECLAIREMENT_UTILE


# Au-dela de ce silence, on considere que la serre etait ARRETEE et on
# ne compte pas le temps ecoule : sinon une coupure d'une nuit passerait
# pour une nuit d'eclairage.
#
# Le trou se juge sur la cadence d'ARCHIVAGE, pas sur celle de lecture :
# c'est l'archive qu'on relit ici. Trois intervalles, jamais moins d'une
# demi-minute -- assez pour absorber un hoquet, assez peu pour qu'une
# coupure ne passe pas pour une heure d'ensoleillement.
TROU_MAXIMAL_S = max(30.0, ARCHIVAGE_S * 3)

REQUETE = """
    WITH eclairee AS (
        SELECT ts,
               valeur >= %s AS utile,
               LEAD(ts) OVER (ORDER BY ts) - ts AS duree
        FROM mesures
        WHERE capteur = %s AND ts >= date_trunc('day', now())
    )
    SELECT COALESCE(SUM(EXTRACT(EPOCH FROM duree)), 0) / 3600.0
    FROM eclairee
    WHERE utile AND duree <= %s * INTERVAL '1 second'
"""


def utile(conn) -> float:
    """La clarte a partir de laquelle la lumiere compte, en pourcent.

    Reglable, parce que « eclaire » n'a pas de valeur universelle : cela
    depend du capteur, de son orientation et de ce qu'on cultive. Tant
    que personne n'a tranche, on garde le defaut du code -- celui avec
    lequel le reseau a ete entraine.

    ATTENTION a ce que ce reglage ne fait PAS : il ne touche que le
    cumul. Le jugement « luminosite instantanee trop faible », lui, a ete
    appris par le reseau avec `ECLAIREMENT_UTILE`, et seul un
    reentrainement l'en ferait changer. Les deux chiffres peuvent donc
    diverger, et c'est assume : l'un dit ce qui compte dans un budget,
    l'autre ce qui declenche une action tout de suite.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT utile FROM eclairement")
        ligne = cur.fetchone()
    return float(ligne[0]) if ligne else float(ECLAIREMENT_UTILE)


def regler(conn, valeur: float) -> None:
    """Pose le seuil de lumiere utile, en remplacant le precedent."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO eclairement (seul, utile, modifie_le)
               VALUES (true, %s, now())
               ON CONFLICT (seul) DO UPDATE SET
                   utile = EXCLUDED.utile,
                   modifie_le = now()""",
            (float(valeur),),
        )


def heures_du_jour(conn, capteur: str = "luminosite") -> float:
    """Heures d'eclairement utile accumulees depuis minuit."""
    seuil = utile(conn)
    with conn.cursor() as cur:
        cur.execute(REQUETE, (seuil, capteur, TROU_MAXIMAL_S))
        ligne = cur.fetchone()
    return round(float(ligne[0]) if ligne and ligne[0] is not None else 0.0, 3)
