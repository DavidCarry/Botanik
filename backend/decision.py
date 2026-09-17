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

# Duree pendant laquelle une regle s'efface apres une commande manuelle.
#
# Reprendre la main doit avoir un effet : sans ce delai, la regle
# remettrait l'actionneur dans SON etat deux secondes plus tard, et
# l'interrupteur reviendrait tout seul sous le doigt.
#
# Trente secondes, et non cinq minutes comme au depart. Ce verrou datait
# d'une epoque ou les regles venaient du modele et non de l'utilisateur :
# se proteger de sa propre consigne pendant cinq minutes, sans que rien
# ne l'affiche, donnait une serre qui « ne fait rien » sans dire
# pourquoi. L'ecran l'annonce desormais, et le delai tient dans le temps
# d'un essai.
VERROU_MANUEL_S = 30

# ---------------------------------------------------------------
# Les sujets d'une regle de visage
# ---------------------------------------------------------------
#
# Une regle de visage se lit « quand UNTEL est devant la camera, faire
# ceci ». Le sujet est le nom d'une personne apprise, ou l'un des deux
# sujets ci-dessous, qui ne designent personne en particulier.

# Le nom que porte un visage que la serre ne reconnait pas. Il vient du
# service de detection et sert ici de sujet : « un inconnu est la ».
ANONYME = "Personne"

# N'importe qui, connu ou non.
QUICONQUE = "quiconque"

# Un visage detecte qui ne correspond a aucune reference.
INCONNU = "inconnu"

# Personne ne peut porter ces noms : ils designent deja autre chose.
SUJETS_RESERVES = (QUICONQUE, INCONNU, ANONYME.lower())

# Duree pendant laquelle une personne reste tenue pour presente apres
# sa derniere detection.
#
# La detection saute une image des qu'on tourne la tete ou qu'on cligne
# des yeux. Sans ce delai, un actionneur commande par un visage
# clignoterait -- exactement le probleme que l'hysteresis regle pour les
# bornes, et pour la meme raison.
PRESENCE_S = 3.0

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


def plage(regle: Regle | None, appris: dict | None) -> dict | None:
    """Les bornes a AFFICHER pour une grandeur, ou None s'il n'y en a pas.

    Exactement la meme resolution que celle qui decide -- meme fonction,
    memes modes. C'est ce qui garantit que la ligne tracee sur la courbe
    est bien celle qui declenchera l'alerte : deux calculs separes
    finiraient par diverger, et l'ecran mentirait sans qu'on le sache.

    Une borne peut manquer, et ce n'est pas une erreur : « au-dessus de
    50, tout va bien » est une consigne complete. L'autre cote vaut
    alors l'infini, et rien n'est trace de ce cote-la.
    """
    if regle is None:
        return None
    connus = appris or {}
    bas = _borne_effective(regle.bas, connus.get("bas"))
    haut = _borne_effective(regle.haut, connus.get("haut"))
    if bas is None and haut is None:
        return None
    return {"bas": bas, "haut": haut}


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


def action_depuis(brut) -> Action | None:
    """Convertit ce qui vient de la base en action, ou None.

    Ici, et non dans un module de table : deux tables portent des
    actions -- les bornes et les visages -- et une seule forme doit
    faire foi.
    """
    if not brut:
        return None
    if isinstance(brut, str):
        import json
        brut = json.loads(brut)
    return Action(
        genre=brut.get("genre", "aucun"),
        cible=brut.get("cible"),
        valeur=brut.get("valeur"),
        texte=brut.get("texte"),
    )


def action_vers(action: Action | None) -> dict | None:
    """La meme chose en sens inverse, pour la base et pour l'interface."""
    if action is None or action.genre == "aucun":
        return None
    return {"genre": action.genre, "cible": action.cible,
            "valeur": action.valeur, "texte": action.texte}


def devant(sujet: str, presents: set[str]) -> bool:
    """Ce sujet est-il devant la camera en ce moment ?

    `presents` porte les noms reconnus, et « Personne » des qu'un visage
    n'a ete rattache a aucune reference.
    """
    if sujet == QUICONQUE:
        return bool(presents)
    if sujet == INCONNU:
        return ANONYME in presents
    return sujet in presents


def _appliquer(ordres: dict, affichages: dict, action: Action | None,
               actif: bool) -> None:
    """Traduit une action, et l'etat de son declencheur, en ordre.

    Le SEUL endroit qui sache ce que declencher veut dire. Les bornes et
    les visages y passent tous les deux : c'est ce qui garantit qu'une
    action se comporte pareil, quelle que soit la raison qui l'a
    reveillee.
    """
    if action is None or action.genre == "aucun":
        return

    if action.genre == "ecran":
        if actif and (action.cible or "ecran") not in affichages:
            affichages[action.cible or "ecran"] = action
        return

    if action.genre == "actionneur" and action.cible:
        vise = float(action.valeur or 0.0)
        # Au repos, l'actionneur revient a l'inverse de ce que l'action
        # demande : sans cela, un bipeur declenche par un reservoir vide
        # sonnerait encore une fois rempli.
        voulu = vise if actif else (0.0 if vise > 0 else 1.0)
        # Une regle active ne se laisse pas ecraser par une regle au
        # repos.
        if actif or action.cible not in ordres:
            ordres[action.cible] = Commande(voulu, "regle")


def _declenchements(regles: dict[str, Regle],
                    franchis: dict[str, str | None],
                    regles_visages: dict[str, Action],
                    presents: set[str]):
    """Chaque action reglee par l'utilisateur, avec son etat du moment.

    Les bornes d'abord, les visages ensuite. L'ordre ne compte que pour
    departager deux regles actives sur le meme actionneur -- il est
    arbitraire, mais stable.
    """
    for grandeur in GRANDEURS:
        regle = regles.get(grandeur)
        if regle is None:
            continue
        yield regle.action_bas, franchis.get(grandeur) == "bas"
        yield regle.action_haut, franchis.get(grandeur) == "haut"

    for sujet, action in regles_visages.items():
        yield action, devant(sujet, presents)


def decider(regles: dict[str, Regle],
            franchis: dict[str, str | None],
            regles_visages: dict[str, Action] | None = None,
            presents: set[str] | None = None) -> dict[str, Commande]:
    """Les etats voulus des actionneurs, d'apres les regles seules.

    Deux sources de declenchement, traitees ensemble : une borne
    franchie, et une personne devant la camera. Elles aboutissent aux
    memes actions et se disputent les memes actionneurs -- les melanger
    ici plutot que de les additionner apres coup est ce qui evite que
    deux regles commandent la meme LED chacune de leur cote.
    """
    ordres: dict[str, Commande] = {}
    affichages: dict[str, Action] = {}

    for action, actif in _declenchements(regles, franchis,
                                         regles_visages or {},
                                         presents or set()):
        _appliquer(ordres, affichages, action, actif)

    for cible, action in affichages.items():
        ordres[cible] = Commande(1.0, "regle", action.texte)

    return ordres
