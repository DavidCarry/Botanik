"""Drivers materiels.

Deux sens de circulation, deux tables :

  DRIVERS  lecture  -- `lire(capteur_id, params) -> float`
  SORTIES  ecriture -- `appliquer(actionneur_id, valeur, params) -> float`

Ajouter un type de materiel = creer un module ici et l'inscrire dans la
table correspondante ; ni les services ni le reste de la chaine n'ont a
changer. Un meme module peut figurer dans les deux, comme `simule`.
"""

from . import mcp3004, simule

DRIVERS = {
    "simule": simule,
    # Les quatre capteurs de la serre sont analogiques et partagent le
    # meme convertisseur : une seule entree ici, quatre voies au registre.
    "mcp3004": mcp3004,
}

SORTIES = {
    "simule": simule,
    # a venir, quand la carte de relais sera montee :
    # "gpio": gpio,         une broche par actionneur
}
