"""Gestion des comptes qui peuvent piloter la serre.

  python comptes.py lister
  python comptes.py ajouter <identifiant> [mot de passe]
  python comptes.py retirer <identifiant>

Le compte `admin` se cree tout seul au premier demarrage de l'API, avec
un mot de passe tire au hasard et imprime une seule fois. Ajouter un
deuxieme compte demandait jusqu'ici d'ecrire du SQL a la main -- donc de
recommencer a chaque base neuve, sans trace dans le depot.

Sans mot de passe en argument, il est tire au hasard et affiche une fois.
Le donner en clair sur la ligne de commande le laisse dans l'historique
du shell : a reserver aux machines de developpement.
"""

import secrets
import sys

import auth
import bdd
import schema


def lister(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT identifiant, cree_le FROM utilisateurs ORDER BY cree_le")
        lignes = cur.fetchall()
    if not lignes:
        print("aucun compte")
        return
    for identifiant, cree_le in lignes:
        print(f"  {identifiant:20} cree le {cree_le:%d/%m/%Y a %H:%M}")


def ajouter(conn, identifiant: str, mot_de_passe: str | None) -> None:
    mot_de_passe = mot_de_passe or secrets.token_urlsafe(9)
    with conn.cursor() as cur:
        # Reutiliser l'identifiant remplace le mot de passe : c'est aussi
        # la seule facon d'en changer un oublie.
        cur.execute(
            "INSERT INTO utilisateurs (identifiant, empreinte) VALUES (%s, %s) "
            "ON CONFLICT (identifiant) DO UPDATE SET empreinte = EXCLUDED.empreinte",
            (identifiant, auth.hacher(mot_de_passe)),
        )
    print(f"compte {identifiant} en place -- mot de passe : {mot_de_passe}")


def retirer(conn, identifiant: str) -> None:
    with conn.cursor() as cur:
        # Les sessions ouvertes partent avec le compte : retirer un acces
        # sans fermer ses sessions ne retire rien pendant sept jours.
        cur.execute("DELETE FROM sessions WHERE compte_id IN "
                    "(SELECT id FROM utilisateurs WHERE identifiant = %s)",
                    (identifiant,))
        cur.execute("DELETE FROM utilisateurs WHERE identifiant = %s", (identifiant,))
        efface = cur.rowcount
    print(f"compte {identifiant} retire" if efface else f"{identifiant} introuvable")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip())
        return 1

    action, arguments = sys.argv[1], sys.argv[2:]
    with bdd.connexion() as conn:
        schema.preparer(conn)
        if action == "lister":
            lister(conn)
        elif action == "ajouter" and arguments:
            ajouter(conn, arguments[0], arguments[1] if len(arguments) > 1 else None)
        elif action == "retirer" and arguments:
            retirer(conn, arguments[0])
        else:
            print(__doc__.strip())
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
