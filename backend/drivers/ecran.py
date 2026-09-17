"""Driver de l'afficheur LCD 16x2, sur son extenseur I2C.

Le driver ne decide pas de ce qui s'affiche : il recoit deux lignes
toutes faites et les ecrit. Composer le texte -- aller chercher la
derniere mesure d'un capteur, la mettre en forme -- releve du service,
qui connait le registre et recoit les mesures. Un driver qui irait lire
des mesures serait un driver qu'on ne peut pas essayer sans la serre.

L'afficheur n'est reecrit que lorsque le texte CHANGE. Sans cela, on lui
enverrait deux trames I2C par seconde pour redessiner la meme chose, et
l'ecran clignoterait a chaque rafraichissement.
"""

import unicodedata

COLONNES = 16
LIGNES = 2

_ecrans = {}
# Dernier texte reellement envoye, par actionneur.
_affiche = {}


def _lcd(params):
    adresse = params.get("adresse", 0x27)
    if adresse not in _ecrans:
        from RPLCD.i2c import CharLCD
        _ecrans[adresse] = CharLCD(
            i2c_expander=params.get("extenseur", "PCF8574"),
            address=adresse,
            port=params.get("port", 1),
            cols=COLONNES,
            rows=LIGNES,
        )
    return _ecrans[adresse]


def _lisible(texte: str) -> str:
    """Ramene le texte a ce que l'afficheur sait dessiner.

    Un HD44780 ne connait pas les accents : « Température » y sortirait
    en caracteres japonais. On les retire plutot que de les laisser
    produire du bruit, et on coupe a la largeur de l'ecran.
    """
    sans_accent = unicodedata.normalize("NFKD", texte)
    sans_accent = "".join(c for c in sans_accent if not unicodedata.combining(c))
    propre = "".join(c if 32 <= ord(c) < 127 else " " for c in sans_accent)
    return propre[:COLONNES]


def appliquer(actionneur_id, valeur, params, lignes=None):
    """Allume ou eteint l'afficheur, et y ecrit les deux lignes recues."""
    lcd = _lcd(params)
    allume = float(valeur) > 0

    if not allume:
        if _affiche.get(actionneur_id) is not None:
            lcd.clear()
            _affiche[actionneur_id] = None
        lcd.backlight_enabled = False
        return 0.0

    lcd.backlight_enabled = True
    texte = tuple(_lisible(l) for l in (list(lignes or []) + ["", ""])[:LIGNES])
    if _affiche.get(actionneur_id) != texte:
        lcd.clear()
        for i, ligne in enumerate(texte):
            lcd.cursor_pos = (i, 0)
            lcd.write_string(ligne)
        _affiche[actionneur_id] = texte
    return 1.0
