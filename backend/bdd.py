"""Ouverture d'une connexion a la base, en un seul endroit.

Cinq modules ouvraient leur propre connexion, chacun avec ses options :
l'un posait un delai d'attente, l'autre non, un troisieme oubliait
l'autocommit. Une politique d'acces qui varie selon le fichier finit par
produire un service qui se bloque et quatre qui tiennent, sans qu'on
sache lequel avait raison.

Ce module ne gere volontairement pas les erreurs : ce qu'il faut faire
d'une base injoignable depend de l'appelant -- l'API repond 503, un
service de fond se plaint et retente au tour suivant.
"""

import psycopg

from config import DB_URL

# Au-dela, on considere la base injoignable plutot que lente. Sans ce
# delai, un service attend indefiniment une machine qui ne repondra pas,
# et rien dans les journaux ne dit pourquoi il s'est tu.
ATTENTE_S = 5


def connexion(*, autocommit: bool = True) -> psycopg.Connection:
    """Connexion courte.

    A cette echelle, ouvrir a la demande coute moins cher a maintenir
    qu'un pool, et evite les connexions mortes au reveil de la Pi.
    """
    return psycopg.connect(DB_URL, connect_timeout=ATTENTE_S, autocommit=autocommit)
