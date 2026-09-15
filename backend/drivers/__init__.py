"""Drivers materiels.

Deux sens de circulation, deux tables :

  DRIVERS  lecture  -- `lire(capteur_id, params) -> float`
  SORTIES  ecriture -- `appliquer(actionneur_id, valeur, params) -> float`

Ajouter un type de materiel = creer un module ici et l'inscrire dans la
table correspondante ; ni les services ni le reste de la chaine n'ont a
changer. Un meme module peut figurer dans les deux, comme `simule`.
"""

from . import simule

DRIVERS = {
    "simule": simule,
    # a venir, quand le materiel arrivera :
    # "ads1115": ads1115,   analogique (humidite du sol)
    # "bme280":  bme280,    I2C (temperature / humidite de l'air)
    # "ds18b20": ds18b20,   1-Wire (temperature du sol)
    # "bh1750":  bh1750,    I2C (luminosite)
}

SORTIES = {
    "simule": simule,
    # a venir, quand la carte de relais sera montee :
    # "gpio": gpio,         une broche par actionneur
}
