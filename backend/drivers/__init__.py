"""Drivers materiels.

Deux sens de circulation, deux tables :

  DRIVERS  lecture  -- `lire(capteur_id, params) -> float`
  SORTIES  ecriture -- `appliquer(actionneur_id, valeur, params) -> float`

Ajouter un type de materiel = creer un module ici et l'inscrire dans la
table correspondante ; ni les services ni le reste de la chaine n'ont a
changer. Un meme module peut figurer dans les deux, comme `simule`.
"""

from . import ds18b20, ecran, gpio, hcsr04, mcp3004, simule

DRIVERS = {
    "simule": simule,
    # Les capteurs analogiques partagent le meme convertisseur : une
    # seule entree ici, une voie par capteur au registre.
    "mcp3004": mcp3004,
    # Sonde numerique sur bus 1-Wire, lue dans un fil separe.
    "ds18b20": ds18b20,
    # Telemetre a ultrasons : il mesure une distance, le registre dit
    # quelle distance vaut plein et laquelle vaut vide.
    "hcsr04": hcsr04,
}

SORTIES = {
    "simule": simule,
    # Tout ce qui s'allume : LED, buzzer, et les relais le jour ou la
    # pompe et la ventilation seront cablees.
    "gpio": gpio,
    # L'afficheur, qui recoit du texte et pas seulement un etat.
    "ecran": ecran,
}
