"""Ce que la serre fait quand elle reconnait quelqu'un.

Meme principe que les regles de bornes, et volontairement la meme forme
d'action : allumer un actionneur, ou afficher un texte. Seul le
declencheur change -- une personne devant la camera au lieu d'une
mesure qui passe une borne.

Le sujet d'une regle est le nom d'une personne apprise, ou l'un des deux
sujets qui ne designent personne en particulier : « quiconque » et
« inconnu ».

Un sujet ABSENT de la table ne declenche rien. C'est l'etat de depart :
la serre reconnait les gens sans rien en faire tant qu'on ne le lui a
pas demande.
"""

from psycopg.types.json import Jsonb

from decision import Action, action_depuis, action_vers


def lire(conn) -> dict[str, Action]:
    """Toutes les regles, prêtes pour le moteur de decision."""
    with conn.cursor() as cur:
        cur.execute("SELECT sujet, action FROM regles_visages")
        lignes = cur.fetchall()

    regles = {}
    for sujet, brut in lignes:
        action = action_depuis(brut)
        if action is not None:
            regles[sujet] = action
    return regles


def brutes(conn) -> dict[str, dict]:
    """Les regles telles quelles, pour l'interface qui les edite."""
    return {sujet: action_vers(action) for sujet, action in lire(conn).items()}


def enregistrer(conn, sujet: str, action: Action) -> None:
    """Pose ou remplace la regle d'un sujet."""
    if action.genre not in ("actionneur", "ecran"):
        raise ValueError(f"genre d'action inconnu : {action.genre}")
    if action.genre == "actionneur" and not action.cible:
        raise ValueError("une action sur actionneur demande une cible")

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO regles_visages (sujet, action, modifie_le)
               VALUES (%s, %s, now())
               ON CONFLICT (sujet) DO UPDATE SET
                   action = EXCLUDED.action,
                   modifie_le = now()""",
            (sujet, Jsonb(action_vers(action))),
        )


def retirer(conn, sujet: str) -> bool:
    """Supprime la regle d'un sujet. La serre continue de le reconnaitre,
    elle cesse simplement d'en faire quelque chose."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM regles_visages WHERE sujet = %s", (sujet,))
        return cur.rowcount > 0
