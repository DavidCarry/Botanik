"""Ce que chaque afficheur montre, d'un demarrage a l'autre.

Le contenu d'un ecran est un REGLAGE, pas un etat -- et c'est toute la
difference. Une pompe repart a l'arret apres une coupure, par prudence :
un souvenir d'avant la panne n'a plus forcement de sens, et une pompe qui
redemarre seule peut noyer la serre. Rien de tel pour un ecran. Le voir
revenir eteint et regle sur la premiere mesure venue apres chaque
deploiement n'est pas prudent, c'est juste cassé.

Ce reglage rejoint donc les bornes et les regles de visages : il vit en
base, et le service le retrouve au demarrage.
"""

from psycopg.types.json import Jsonb


def lire(conn) -> dict[str, tuple[dict, bool]]:
    """Le reglage de chaque afficheur : quoi montrer, et s'il etait allume."""
    with conn.cursor() as cur:
        cur.execute("SELECT actionneur, contenu, allume FROM afficheurs")
        return {a: (contenu, bool(allume)) for a, contenu, allume in cur.fetchall()}


def enregistrer(conn, actionneur: str, contenu: dict, allume: bool) -> None:
    """Retient le reglage d'un afficheur, en remplacant le precedent."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO afficheurs (actionneur, contenu, allume, modifie_le)
               VALUES (%s, %s, %s, now())
               ON CONFLICT (actionneur) DO UPDATE SET
                   contenu = EXCLUDED.contenu,
                   allume = EXCLUDED.allume,
                   modifie_le = now()""",
            (actionneur, Jsonb(contenu), allume),
        )
