"""Ce que la serre doit faire, a partir de ce que le reseau a juge.

Le coeur metier du projet, et le seul module qui contienne des regles
plutot que de la tuyauterie. Il ne connait ni MQTT, ni la base, ni
NumPy : il prend des jugements et des mesures, il rend des commandes.
On peut donc le verifier entierement sans lancer quoi que ce soit.

La repartition des roles est volontaire :

  le reseau   JUGE      chaque grandeur est-elle trop basse, trop haute ?
  ce module   AGIT      que faire de ces jugements
  le cerveau  CADENCE   quand decider, combien de temps actionner

Un reseau qui commanderait directement la pompe melangerait ce qu'il
sait faire -- reconnaitre une situation -- avec ce qui doit rester
explicite et verifiable : ne jamais pomper a sec.
"""

from typing import NamedTuple

# Les grandeurs jugees par le reseau. L'eclairement du jour n'est pas une
# mesure de capteur mais un cumul : le temps passe sous une lumiere
# suffisante depuis minuit. C'est lui qui porte le budget quotidien.
GRANDEURS = [
    "humidite_sol_a",
    "temperature_air",
    "luminosite",
    "niveau_eau",
    "eclairement_jour",
]

# Duree pendant laquelle le modele s'efface apres une commande manuelle.
#
# Reprendre la main doit avoir un effet durable : sans ce delai, le
# modele remettrait l'actionneur dans SON etat a la decision suivante --
# trente secondes plus tard -- et l'interrupteur reviendrait tout seul
# sous le doigt de l'utilisateur.
#
# Le garde-fou de securite, lui, n'est jamais verrouille : si la reserve
# se vide pendant un arrosage manuel, la pompe doit s'arreter malgre
# tout. Une pompe grillee ne se discute pas.
VERROU_MANUEL_S = 300

# Sous ce niveau, la pompe est bloquee quoi qu'il arrive. Ce n'est pas le
# seuil d'alerte -- celui-la, le reseau l'apprend -- mais un plancher
# materiel : une pompe qui tourne a sec s'abime en quelques secondes.
# Pas zero : un flotteur bruite passe sous zero avant d'y arriver.
PLANCHER_POMPE = 5.0


class Jugement(NamedTuple):
    """Ce que le reseau pense d'une grandeur."""
    bas: bool
    haut: bool


class Commande(NamedTuple):
    valeur: float
    source: str      # "ia" ou "securite"

# Marge d'hysteresis, exprimee sur la CERTITUDE du reseau et non sur les
# unites de chaque grandeur.
#
# Sans elle, une mesure qui oscille autour de sa frontiere fait osciller
# le jugement avec elle : l'alerte s'ouvre, se ferme, se rouvre, et le
# journal se remplit de bruit pendant que la pompe bat la mesure. Le
# reseau, lui, ne se trompe pas -- il dit honnetement « 50,4 % puis
# 49,6 % ». C'est notre lecture binaire qui est trop nerveuse.
#
# On ouvre donc a la moitie, et on ne referme qu'en dessous : tant que le
# reseau reste hesitant, l'etat en cours tient. Une grandeur vraiment
# revenue dans sa plage fait chuter la probabilite bien plus bas que
# cette marge, donc l'alerte se leve normalement.
#
# La marge porte sur la certitude plutot que sur les degres ou les lux :
# une seule regle vaut alors pour les cinq grandeurs, sans avoir a
# choisir a la main ce que « un peu » veut dire pour chacune.
CERTITUDE_OUVERTURE = 0.50
CERTITUDE_FERMETURE = 0.35



def _tenir(probabilite: float, actif: bool) -> bool:
    """Le seuil a franchir depend de l'etat en cours : c'est tout le
    principe de l'hysteresis."""
    return probabilite >= (CERTITUDE_FERMETURE if actif else CERTITUDE_OUVERTURE)



def juger(probabilites: dict[str, float],
          precedents: dict[str, Jugement] | None = None) -> dict[str, Jugement]:
    """Les jugements du reseau, lus avec hysteresis.

    `probabilites` est indexe par sortie -- « humidite_sol_a_bas » -- et
    `precedents` porte les jugements du tour d'avant. Vide au premier
    tour : tout part alors de la simple moitie, sans etat a retenir.
    """
    anciens = precedents or {}
    nouveaux: dict[str, Jugement] = {}
    for grandeur in GRANDEURS:
        avant = anciens.get(grandeur, Jugement(False, False))
        nouveaux[grandeur] = Jugement(
            _tenir(probabilites.get(f"{grandeur}_bas", 0.0), avant.bas),
            _tenir(probabilites.get(f"{grandeur}_haut", 0.0), avant.haut),
        )
    return nouveaux


# Ce qui merite d'alerter, et sous quel nom.
#
# Tous les jugements n'en sont pas. « Luminosite trop basse » est vrai
# chaque nuit, « reserve pleine » est une bonne nouvelle, et « pas encore
# assez de lumiere aujourd'hui » est l'etat normal d'une matinee. En
# faire des alertes noierait les vraies sous le bruit, et plus personne
# ne regarderait le voyant.
#
# `humaine` distingue ce que la serre ne peut PAS corriger seule : il
# faut alors quelqu'un. C'est ce qui justifie le bipeur.
ALERTES: dict[tuple[str, str], dict] = {
    ("humidite_sol_a", "bas"): {"libelle": "Sol trop sec", "humaine": False},
    ("humidite_sol_a", "haut"): {"libelle": "Sol détrempé", "humaine": False},
    ("temperature_air", "bas"): {"libelle": "Trop froid", "humaine": True},
    ("temperature_air", "haut"): {"libelle": "Trop chaud", "humaine": True},
    ("luminosite", "haut"): {"libelle": "Lumière excessive", "humaine": True},
    ("niveau_eau", "bas"): {"libelle": "Réserve d'eau basse", "humaine": True},
    ("eclairement_jour", "haut"): {"libelle": "Trop de lumière aujourd'hui",
                                   "humaine": False},
}



def alertes(jugements: dict[str, Jugement]) -> dict[str, str | None]:
    """Pour chaque grandeur, le cote en alerte, ou None si tout va bien.

    Une seule alerte par grandeur : elle ne peut pas etre trop basse et
    trop haute a la fois. Le cote suffit donc a la designer.
    """
    ouvertes: dict[str, str | None] = {}
    for grandeur in GRANDEURS:
        j = jugements.get(grandeur, Jugement(False, False))
        cote = None
        if j.bas and (grandeur, "bas") in ALERTES:
            cote = "bas"
        elif j.haut and (grandeur, "haut") in ALERTES:
            cote = "haut"
        ouvertes[grandeur] = cote
    return ouvertes



def decider(jugements: dict[str, Jugement],
            mesures: dict[str, float]) -> dict[str, Commande]:
    """Les etats voulus pour chaque actionneur pilote par le modele.

    Renvoie des ETATS, pas des impulsions : la duree d'un arrosage ou la
    cadence d'une alerte sonore relevent du temps, donc du cerveau.
    """
    ordres: dict[str, Commande] = {}

    def juge(grandeur: str) -> Jugement:
        return jugements.get(grandeur, Jugement(False, False))

    # ---- humidite du sol : les deux actionneurs qui la corrigent ----
    sol = juge("humidite_sol_a")
    ordres["pompe"] = Commande(1.0 if sol.bas else 0.0, "ia")
    ordres["ventilation"] = Commande(1.0 if sol.haut else 0.0, "ia")

    # ---- reserve d'eau : alerter, et proteger la pompe ----
    eau = juge("niveau_eau")
    ordres["bipeur"] = Commande(1.0 if eau.bas else 0.0, "ia")

    niveau = mesures.get("niveau_eau")
    if niveau is not None and niveau <= PLANCHER_POMPE:
        # Prime sur la decision du reseau, meme s'il a raison par ailleurs.
        ordres["pompe"] = Commande(0.0, "securite")

    # ---- lumiere : un budget quotidien, pas un seuil instantane ----
    # Trop peu de lumiere recue aujourd'hui : on eclaire jusqu'a combler.
    # Assez, ou trop : on eteint. La plante a besoin de nuit autant que
    # de jour.
    jour = juge("eclairement_jour")
    ordres["lumiere"] = Commande(1.0 if jour.bas and not jour.haut else 0.0, "ia")

    # ---- temperature : jugee, mais rien ne peut agir dessus ----
    # Le seuil sert a l'affichage et a l'alerte visuelle, pas a une
    # commande. Aucune resistance ni climatisation dans le montage.

    return ordres
