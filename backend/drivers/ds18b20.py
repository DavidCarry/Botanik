"""Driver de la sonde de temperature DS18B20, sur bus 1-Wire.

Une sonde lente, et c'est tout le probleme qu'elle pose.

Le DS18B20 met environ 800 ms a convertir une temperature en douze bits,
et le noyau declenche cette conversion a CHAQUE lecture du fichier. Le
publisher, lui, passe toutes les 500 ms : le lire directement bloquerait
la boucle et retarderait les trois autres capteurs, qui n'y sont pour
rien.

La lecture se fait donc dans un fil separe, qui tourne a son rythme, et
`lire()` rend la derniere valeur connue -- instantanement. Une
temperature d'il y a deux secondes est de toute facon la meme : ce qui
serait faux, c'est de faire attendre le reste de la serre pour l'obtenir
a la milliseconde pres.

Le bus verifie ses trames : chaque lecture porte un CRC, et une trame
douteuse est rejetee plutot que servie. Un fil debranche produit des
octets plausibles, pas des octets justes.
"""

import threading
import time
from pathlib import Path

RACINE = Path("/sys/bus/w1/devices")

# Repos entre deux lectures.
#
# Ce n'est PAS la cadence de rafraichissement : la conversion elle-meme
# prend environ 800 ms en douze bits, et c'est elle qui commande. Deux
# secondes de repos donnaient une valeur nouvelle toutes les trois
# secondes, la ou les autres capteurs se renouvellent deux fois par
# seconde -- l'ecart se voyait.
#
# A 200 ms, la sonde tourne pratiquement en continu et rend une valeur
# neuve chaque seconde. C'est son plafond materiel : descendre plus bas
# imposerait de baisser sa resolution, ce qui demande les droits root.
PERIODE_S = 0.2

# Au-dela, la derniere valeur est jugee perimee et le driver echoue --
# ce qui fait basculer le publisher sur la simulation, en le disant.
PEREMPTION_S = 15.0

# Derniere lecture valide par sonde, et fils deja lances.
_valeurs: dict[str, tuple[float, float]] = {}
_fils: dict[str, threading.Thread] = {}
_verrou = threading.Lock()


def _lire_fichier(identifiant: str) -> float:
    """Une conversion, CRC verifie. Leve si la trame est douteuse."""
    brut = (RACINE / identifiant / "w1_slave").read_text()
    lignes = brut.strip().splitlines()
    if len(lignes) < 2 or not lignes[0].rstrip().endswith("YES"):
        raise ValueError("trame rejetee par le controle d'integrite")
    _, _, milli = lignes[1].partition("t=")
    if not milli:
        raise ValueError("trame sans temperature")
    return int(milli) / 1000.0


def _boucler(identifiant: str) -> None:
    while True:
        try:
            valeur = _lire_fichier(identifiant)
            with _verrou:
                _valeurs[identifiant] = (valeur, time.monotonic())
        except Exception:
            # On ne se plaint pas ici : le fil n'a pas de journal a lui,
            # et le publisher dira de toute facon que la sonde ne repond
            # plus des que la derniere valeur aura vieilli.
            pass
        time.sleep(PERIODE_S)


def _demarrer(identifiant: str) -> None:
    """Un fil par sonde, lance a la premiere demande et jamais arrete."""
    if identifiant in _fils:
        return
    fil = threading.Thread(target=_boucler, args=(identifiant,), daemon=True)
    _fils[identifiant] = fil
    fil.start()


def lire(capteur_id, params):
    """La derniere temperature connue, sans jamais attendre la sonde."""
    identifiant = params["identifiant"]
    if identifiant not in _fils:
        _demarrer(identifiant)
        # Premiere lecture en direct : sans elle, le capteur passerait
        # pour absent pendant la seconde qui suit le demarrage, et
        # l'ecran afficherait « simule » sans raison.
        valeur = _lire_fichier(identifiant)
        with _verrou:
            _valeurs[identifiant] = (valeur, time.monotonic())
        return round(valeur, 2)

    with _verrou:
        connue = _valeurs.get(identifiant)
    if connue is None:
        raise RuntimeError("aucune lecture valide de la sonde")

    valeur, instant = connue
    age = time.monotonic() - instant
    if age > PEREMPTION_S:
        raise RuntimeError(f"derniere lecture valide il y a {age:.0f} s")
    return round(valeur, 2)
