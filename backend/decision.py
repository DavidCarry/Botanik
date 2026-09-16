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
