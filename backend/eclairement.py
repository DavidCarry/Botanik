"""Le temps passe sous une lumiere suffisante depuis minuit.

Ni une mesure de capteur, ni un etat a maintenir quelque part : un cumul
qui se recalcule depuis l'historique deja archive. La base sait a quelle
heure la luminosite a franchi le seuil utile et pendant combien de temps
elle s'y est tenue -- il suffit de le lui demander.

L'avantage sur un compteur entretenu en memoire : un service qui
redemarre a midi retrouve immediatement le bon cumul, au lieu de repartir
de zero et de rallumer la lampe pour rien.
"""

from config import ARCHIVAGE_S

# Au-dela de ce niveau, la plante est consideree eclairee. En dessous,
# la lumiere est trop faible pour compter dans son budget.
LUX_UTILE = 3000.0

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


def heures_du_jour(conn, capteur: str = "luminosite") -> float:
    """Heures d'eclairement utile accumulees depuis minuit."""
    with conn.cursor() as cur:
        cur.execute(REQUETE, (LUX_UTILE, capteur, TROU_MAXIMAL_S))
        ligne = cur.fetchone()
    return round(float(ligne[0]) if ligne and ligne[0] is not None else 0.0, 3)
