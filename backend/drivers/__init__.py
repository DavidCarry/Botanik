"""Drivers de capteurs.

Chaque driver expose `lire(capteur_id, params) -> float`. Ajouter un type de
capteur = creer un module ici et l'inscrire dans DRIVERS ; ni le publisher ni
le reste de la chaine n'ont a changer.
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
