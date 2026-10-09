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


# Les deux facons de fixer la clarte utile. Memes noms que les bornes
# d'une regle, et pour la meme raison : c'est la meme promesse. « ia »
# suit ce que le reseau a appris, « manuel » suit le chiffre qu'on tape.
# Pas de « aucun » : le cumul a toujours besoin d'une definition.
MODES = ("ia", "manuel")


def reglage(conn) -> dict:
    """Le mode choisi, le chiffre saisi, et ce que « ia » vaut.

    Les trois, parce que l'ecran a besoin des trois : le mode pour
    savoir quelle pilule allumer, la valeur pour remplir le champ, et le
    seuil appris pour annoncer ce que « ia » donne.

    « ia » vaut `ECLAIREMENT_UTILE`, c'est-a-dire la clarte sur laquelle
    le reseau a ETE ENTRAINE -- et non la frontiere qu'on lirait en le
    balayant. Meme raison que pour le budget du jour dans `seuils.py` :
    l'etiquette apprise est une constante, et la frontiere balayee n'en
    est qu'une approximation bruitee, qui donnerait un seuil different a
    chaque relecture sans que rien n'ait change.

    Table vide = personne n'a tranche, et le mode est alors « ia ».
    """
    with conn.cursor() as cur:
        cur.execute("SELECT mode, utile FROM eclairement")
        ligne = cur.fetchone()
    mode, valeur = ligne if ligne else ("ia", None)
    return {
        "mode": mode,
        "valeur": None if valeur is None else float(valeur),
        "appris": float(ECLAIREMENT_UTILE),
    }


def utile(conn) -> float:
    """La clarte a partir de laquelle la lumiere compte, en pourcent.

    Reglable, parce que « eclaire » n'a pas de valeur universelle : cela
    depend du capteur, de son orientation et de ce qu'on cultive.

    ATTENTION a ce que ce reglage ne fait PAS : il ne touche que le
    cumul. Le jugement « luminosite instantanee trop faible », lui, a ete
    appris par le reseau avec `ECLAIREMENT_UTILE`, et seul un
    reentrainement l'en ferait changer. En mode « ia » les deux chiffres
    coincident donc par construction ; en « manuel » ils peuvent
    diverger, et c'est assume -- l'un dit ce qui compte dans un budget,
    l'autre ce qui declenche une action tout de suite.

    Un mode « manuel » sans chiffre retombe sur l'appris plutot que de
    lever : l'API refuse deja ce cas, et un cumul qui s'arrete parce
    qu'une case est vide serait une panne pour un reglage.
    """
    choisi = reglage(conn)
    if choisi["mode"] == "manuel" and choisi["valeur"] is not None:
        return choisi["valeur"]
    return choisi["appris"]


def regler(conn, mode: str, valeur: float | None) -> None:
    """Pose le reglage de clarte, en remplacant le precedent.

    La valeur est gardee meme en mode « ia », ou elle ne sert a rien :
    repasser en manuel retrouve ainsi le dernier chiffre tape, au lieu
    d'un champ vide a remplir de nouveau.
    """
    if mode not in MODES:
        raise ValueError(f"mode inconnu : {mode}")
    if mode == "manuel" and valeur is None:
        raise ValueError("un reglage manuel demande une valeur")

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO eclairement (seul, mode, utile, modifie_le)
               VALUES (true, %s, %s, now())
               ON CONFLICT (seul) DO UPDATE SET
                   mode = EXCLUDED.mode,
                   utile = EXCLUDED.utile,
                   modifie_le = now()""",
            (mode, None if valeur is None else float(valeur)),
        )


def heures_du_jour(conn, capteur: str = "luminosite") -> float:
    """Heures d'eclairement utile accumulees depuis minuit."""
    seuil = utile(conn)
    with conn.cursor() as cur:
        cur.execute(REQUETE, (seuil, capteur, TROU_MAXIMAL_S))
        ligne = cur.fetchone()
    return round(float(ligne[0]) if ligne and ligne[0] is not None else 0.0, 3)
