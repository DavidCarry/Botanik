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

class Jugement(NamedTuple):
    """Ce que le reseau pense d'une grandeur."""
    bas: bool
    haut: bool


class Commande(NamedTuple):
    valeur: float
    # Qui a decide : "regle" pour une regle de l'utilisateur, "manuel"
    # pour un clic. Le journal le garde, et l'ecran l'affiche.
    source: str
    # Texte a afficher, pour le seul afficheur.
    texte: str | None = None


# ---------------------------------------------------------------
# Les regles de l'utilisateur
# ---------------------------------------------------------------
#
# Il n'y a plus AUCUNE regle ecrite en dur. « Sol trop sec, donc
# arroser » etait une decision d'agronome deguisee en code : on ne
# pouvait ni la lire depuis l'ecran, ni la changer sans redeployer, et
# elle mentionnait des actionneurs qui n'existent plus.
#
# Desormais chaque grandeur porte deux bornes et deux actions, que
# l'utilisateur regle depuis l'interface. Une grandeur sans regle ne
# declenche rien : ni alerte, ni commande.
#
# Le reseau n'a pas disparu pour autant -- au contraire, il retrouve son
# vrai role. Il APPREND ou passent les frontieres ; l'utilisateur decide
# quoi en faire. Une borne en mode « ia » suit le seuil appris et se
# deplace donc avec la chaleur et la lumiere ; en mode « manuel » elle
# est fixe ; en mode « aucun » ce cote est ignore.

MODES = ("ia", "manuel", "aucun")

# Marge d'hysteresis sur une borne chiffree, en part de l'etendue du
# capteur.
#
# Meme raison que pour les jugements du reseau : une mesure qui oscille
# autour de la borne ferait battre l'actionneur et remplirait le journal.
# On franchit a la borne, on ne revient qu'apres l'avoir repassee de
# cette marge.
MARGE_BORNE = 0.02


class Borne(NamedTuple):
    mode: str                     # "ia", "manuel" ou "aucun"
    valeur: float | None = None   # seulement en mode "manuel"


class Action(NamedTuple):
    """Ce que la serre fait quand une borne est franchie.

    `genre` vaut "actionneur" -- mettre un actionneur dans un etat --,
    "ecran" -- y afficher un texte -- ou "aucun", pour une grandeur
    qu'on veut surveiller sans rien declencher. La temperature est dans
    ce cas : rien n'est cable pour la corriger.
    """
    genre: str
    cible: str | None = None
    valeur: float | None = None
    texte: str | None = None


class Regle(NamedTuple):
    bas: Borne
    haut: Borne
    action_bas: Action | None = None
    action_haut: Action | None = None


AUCUNE = Action("aucun")


def _borne_effective(borne: Borne, cote_ia: float | None) -> float | None:
    """La valeur a comparer, ou None si ce cote est ignore."""
    if borne.mode == "manuel":
        return borne.valeur
    if borne.mode == "ia":
        return cote_ia
    return None


def cotes_franchis(regles: dict[str, Regle],
                   mesures: dict[str, float],
                   seuils_ia: dict[str, dict],
                   etendues: dict[str, float],
                   precedents: dict[str, str | None]) -> dict[str, str | None]:
    """Pour chaque grandeur reglee, le cote franchi -- ou None.

    `precedents` porte l'etat du tour d'avant : c'est lui qui donne son
    sens a l'hysteresis. Sans memoire, une marge ne sert a rien.
    """
    franchis: dict[str, str | None] = {}

    for grandeur, regle in regles.items():
        valeur = mesures.get(grandeur)
        if valeur is None:
            franchis[grandeur] = None
            continue

        appris = seuils_ia.get(grandeur) or {}
        bas = _borne_effective(regle.bas, appris.get("bas"))
        haut = _borne_effective(regle.haut, appris.get("haut"))
        marge = MARGE_BORNE * etendues.get(grandeur, 100.0)
        avant = precedents.get(grandeur)

        # Sortir demande de repasser la borne d'une marge ; entrer se
        # fait a la borne exacte, pour que le chiffre affiche soit bien
        # celui qui declenche.
        if bas is not None and valeur < (bas + marge if avant == "bas" else bas):
            franchis[grandeur] = "bas"
        elif haut is not None and valeur > (haut - marge if avant == "haut" else haut):
            franchis[grandeur] = "haut"
        else:
            franchis[grandeur] = None

    return franchis


def decider(regles: dict[str, Regle],
            franchis: dict[str, str | None]) -> dict[str, Commande]:
    """Les etats voulus des actionneurs, d'apres les regles seules.

    Une action est MAINTENUE tant que la borne reste franchie, et
    relachee ensuite -- l'actionneur revient alors a l'etat inverse.
    Sans cela, un bipeur declenche par un reservoir vide sonnerait
    encore une fois rempli.

    Deux regles qui se disputent le meme actionneur : celle qui est
    active l'emporte. Si les deux le sont, la premiere dans l'ordre des
    grandeurs decide -- c'est arbitraire, mais c'est stable, et l'ecran
    montre les deux alertes.
    """
    ordres: dict[str, Commande] = {}
    affichages: dict[str, Action] = {}

    for grandeur in GRANDEURS:
        regle = regles.get(grandeur)
        if regle is None:
            continue
        for cote, action in (("bas", regle.action_bas), ("haut", regle.action_haut)):
            if action is None or action.genre == "aucun":
                continue
            actif = franchis.get(grandeur) == cote

            if action.genre == "ecran":
                if actif and action.cible not in affichages:
                    affichages[action.cible or "ecran"] = action
                continue

            if action.genre == "actionneur" and action.cible:
                voulu = float(action.valeur or 0.0) if actif else                     (0.0 if float(action.valeur or 0.0) > 0 else 1.0)
                # Une regle active ne se laisse pas ecraser par une
                # regle au repos.
                if actif or action.cible not in ordres:
                    ordres[action.cible] = Commande(voulu, "regle")

    for cible, action in affichages.items():
        ordres[cible] = Commande(1.0, "regle", action.texte)

    return ordres
