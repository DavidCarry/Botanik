"""Lecture et ecriture des regles definies par l'utilisateur.

La table est la source de verite : le cerveau la relit, l'API l'expose
et la modifie. Rien n'est garde en memoire d'un cote qui ne soit pas
relu de l'autre -- c'est ce qui evite qu'un reglage change a l'ecran
mette dix minutes a s'appliquer, ou pire, ne s'applique jamais.

Une grandeur ABSENTE de la table n'a pas de regle : elle ne declenche ni
alerte ni commande. C'est l'etat de depart, et c'est voulu -- une serre
qui agirait avant qu'on lui ait dit quoi faire serait une serre dont on
ne comprend pas les gestes.
"""

import json

from decision import MODES, Action, Borne, Regle

CHAMPS = """grandeur, mode_bas, mode_haut, valeur_bas, valeur_haut,
            action_bas, action_haut"""


def _action(brut) -> Action | None:
    """Convertit ce qui vient de la base en action, ou None."""
    if not brut:
        return None
    if isinstance(brut, str):
        brut = json.loads(brut)
    return Action(
        genre=brut.get("genre", "aucun"),
        cible=brut.get("cible"),
        valeur=brut.get("valeur"),
        texte=brut.get("texte"),
    )


def _en_json(action: Action | None):
    if action is None or action.genre == "aucun":
        return None
    return {"genre": action.genre, "cible": action.cible,
            "valeur": action.valeur, "texte": action.texte}


def lire(conn) -> dict[str, Regle]:
    """Toutes les regles, prêtes pour le moteur de decision."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT {CHAMPS} FROM regles")
        lignes = cur.fetchall()

    return {
        grandeur: Regle(
            bas=Borne(mode_bas, valeur_bas),
            haut=Borne(mode_haut, valeur_haut),
            action_bas=_action(action_bas),
            action_haut=_action(action_haut),
        )
        for (grandeur, mode_bas, mode_haut, valeur_bas, valeur_haut,
             action_bas, action_haut) in lignes
    }


def brutes(conn) -> list[dict]:
    """Les regles telles quelles, pour l'interface qui les edite."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT {CHAMPS} FROM regles ORDER BY grandeur")
        lignes = cur.fetchall()

    return [
        {
            "grandeur": grandeur,
            "bas": {"mode": mode_bas, "valeur": valeur_bas,
                    "action": _en_json(_action(action_bas))},
            "haut": {"mode": mode_haut, "valeur": valeur_haut,
                     "action": _en_json(_action(action_haut))},
        }
        for (grandeur, mode_bas, mode_haut, valeur_bas, valeur_haut,
             action_bas, action_haut) in lignes
    ]


def enregistrer(conn, grandeur: str, regle: Regle) -> None:
    """Pose ou remplace la regle d'une grandeur."""
    from psycopg.types.json import Jsonb

    for borne in (regle.bas, regle.haut):
        if borne.mode not in MODES:
            raise ValueError(f"mode inconnu : {borne.mode}")
        if borne.mode == "manuel" and borne.valeur is None:
            raise ValueError("une borne manuelle demande une valeur")

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO regles (grandeur, mode_bas, mode_haut, valeur_bas,
                                   valeur_haut, action_bas, action_haut,
                                   modifie_le)
               VALUES (%s, %s, %s, %s, %s, %s, %s, now())
               ON CONFLICT (grandeur) DO UPDATE SET
                   mode_bas = EXCLUDED.mode_bas,
                   mode_haut = EXCLUDED.mode_haut,
                   valeur_bas = EXCLUDED.valeur_bas,
                   valeur_haut = EXCLUDED.valeur_haut,
                   action_bas = EXCLUDED.action_bas,
                   action_haut = EXCLUDED.action_haut,
                   modifie_le = now()""",
            (grandeur, regle.bas.mode, regle.haut.mode,
             regle.bas.valeur, regle.haut.valeur,
             Jsonb(_en_json(regle.action_bas)) if regle.action_bas else None,
             Jsonb(_en_json(regle.action_haut)) if regle.action_haut else None),
        )


def retirer(conn, grandeur: str) -> bool:
    """Supprime la regle d'une grandeur. La serre cesse alors de s'en
    occuper -- ni alerte, ni commande."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM regles WHERE grandeur = %s", (grandeur,))
        return cur.rowcount > 0
