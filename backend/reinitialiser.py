"""Remet la base dans un etat propre.

  python reinitialiser.py            efface l'historique
  python reinitialiser.py --tout     efface aussi les modeles entraines

A utiliser quand les donnees accumulees ne veulent plus rien dire : une
luminosite en lux alors que le capteur rend des pourcentages, une
temperature de 1 degre venue d'une sonde debranchee, des commandes vers
des actionneurs qui n'existent plus. Ces lignes ne sont pas fausses au
sens du stockage -- elles sont simplement d'un autre monde, et les
melanger aux nouvelles rendrait les courbes illisibles.

Ce qui n'est PAS efface : les regles, qui sont des reglages et non de
l'historique, et les comptes.
"""

import sys

import bdd
import schema

HISTORIQUE = ("mesures", "commandes", "alertes", "sessions")


def compter(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table}")
        return cur.fetchone()[0]


def vider(conn, table: str) -> int:
    avant = compter(conn, table)
    with conn.cursor() as cur:
        # TRUNCATE et non DELETE : il rend la place au systeme au lieu de
        # laisser des lignes mortes derriere lui.
        cur.execute(f"TRUNCATE TABLE {table}")
    return avant


def main() -> int:
    tout = "--tout" in sys.argv
    tables = HISTORIQUE + (("modeles",) if tout else ())

    with bdd.connexion() as conn:
        schema.preparer(conn)
        for table in tables:
            print(f"  {table:12} {vider(conn, table):>8} lignes effacees")
        print(f"  {'regles':12} {compter(conn, 'regles'):>8} conservees")
        print(f"  {'utilisateurs':12} {compter(conn, 'utilisateurs'):>8} conserves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
