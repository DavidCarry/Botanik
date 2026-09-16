"""Comptes et sessions.

Choix volontairement sobres : les mots de passe sont haches avec scrypt
(bibliotheque standard, pas de dependance), et les sessions sont des
jetons aleatoires stockes en base plutot que des JWT -- ici il n'y a
qu'un serveur, et un jeton en base se revoque, ce qu'un JWT ne sait pas
faire sans machinerie supplementaire.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

DUREE_SESSION = timedelta(days=7)


def hacher(mot_de_passe: str, sel: bytes | None = None) -> str:
    sel = sel or secrets.token_bytes(16)
    cle = hashlib.scrypt(mot_de_passe.encode(), salt=sel, n=2**14, r=8, p=1, dklen=32)
    return f"{sel.hex()}${cle.hex()}"


def verifier(mot_de_passe: str, empreinte: str) -> bool:
    try:
        sel_hex, _ = empreinte.split("$")
    except ValueError:
        return False
    # compare_digest : le temps de comparaison ne doit pas renseigner
    # l'attaquant sur le nombre de caracteres corrects.
    return hmac.compare_digest(hacher(mot_de_passe, bytes.fromhex(sel_hex)), empreinte)


def compte_initial(conn):
    """Cree un compte s'il n'y en a aucun.

    Renvoie le mot de passe genere quand un compte vient d'etre cree, afin
    qu'il soit affiche une fois au demarrage -- sinon None. Les tables,
    elles, sont creees par schema.py.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM utilisateurs")
        if cur.fetchone()[0] > 0:
            return None

        identifiant = os.getenv("ADMIN_IDENTIFIANT", "admin")
        mot_de_passe = os.getenv("ADMIN_MDP") or secrets.token_urlsafe(9)
        cur.execute(
            "INSERT INTO utilisateurs (identifiant, empreinte) VALUES (%s, %s)",
            (identifiant, hacher(mot_de_passe)),
        )
        return identifiant, mot_de_passe


def ouvrir_session(conn, identifiant: str, mot_de_passe: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, empreinte FROM utilisateurs WHERE identifiant = %s",
            (identifiant,),
        )
        ligne = cur.fetchone()
        if not ligne or not verifier(mot_de_passe, ligne[1]):
            return None

        jeton = secrets.token_urlsafe(32)
        cur.execute(
            "INSERT INTO sessions (jeton, compte_id, expire_le) VALUES (%s, %s, %s)",
            (jeton, ligne[0], datetime.now(timezone.utc) + DUREE_SESSION),
        )
        return jeton


def compte_de(conn, jeton: str | None) -> str | None:
    """Identifiant du porteur du jeton, ou None s'il est absent ou perime."""
    if not jeton:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """SELECT u.identifiant FROM sessions s
               JOIN utilisateurs u ON u.id = s.compte_id
               WHERE s.jeton = %s AND s.expire_le > now()""",
            (jeton,),
        )
        ligne = cur.fetchone()
        return ligne[0] if ligne else None


def fermer_session(conn, jeton: str | None):
    if not jeton:
        return
    with conn.cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE jeton = %s", (jeton,))
