"""Drivers materiels.

Deux sens de circulation, deux tables :

  DRIVERS  lecture  -- `lire(capteur_id, params) -> float`
  SORTIES  ecriture -- `appliquer(actionneur_id, valeur, params) -> float`

Ajouter un type de materiel = creer un module ici et l'inscrire dans la
table correspondante ; ni les services ni le reste de la chaine n'ont a
changer. Un meme module peut figurer dans les deux, comme `simule`.
"""

from . import ecran, gpio, mcp3004, simule

DRIVERS = {
    "simule": simule,
    # Les quatre capteurs de la serre sont analogiques et partagent le
    # meme convertisseur : une seule entree ici, quatre voies au registre.
    "mcp3004": mcp3004,
}

SORTIES = {
    "simule": simule,
    # Tout ce qui s'allume : LED, buzzer, et les relais le jour ou la
    # pompe et la ventilation seront cablees.
    "gpio": gpio,
    # L'afficheur, qui recoit du texte et pas seulement un etat.
    "ecran": ecran,
}
