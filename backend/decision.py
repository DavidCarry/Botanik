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
#
# Une seconde et non trois : le service de detection amortit DEJA une
# demi-seconde de son cote, et trois secondes de plus se voyaient a
# l'oeil -- on s'ecarte de la camera, et la LED reste allumee un temps
# qu'on ne s'explique pas.
PRESENCE_S = 1.0

# ---------------------------------------------------------------
# Qui l'emporte sur l'afficheur
# ---------------------------------------------------------------
#
# Plusieurs messages peuvent se presenter en meme temps. L'ordre est :
#
#   une personne reconnue   passe devant tout
#   une borne franchie      passe devant l'ordinaire
#   l'ordinaire             ce qui reste quand rien d'autre ne parle
#
# Les deux premiers sont des RECOUVREMENTS : ils se posent par-dessus, et
# l'ecran retrouve l'ordinaire des qu'ils se levent. L'ordinaire n'est
# pas connu ici -- c'est le choix de l'utilisateur, garde par le service
# qui pilote l'afficheur.
#
# Les deux origines automatiques portent un NOM, et pas seulement un
# rang : il voyage avec la commande jusqu'au journal, ou « le bipeur
# s'est declenche a cause d'un seuil » et « a cause d'un visage » ne se
# relisent pas de la meme facon. La troisieme origine possible, la main
# de l'utilisateur, ne passe pas par ici.
SEUIL = "seuil"
VISAGE = "visage"

# Qui l'emporte quand les deux veulent l'afficheur en meme temps.
PREPONDERANCE = {SEUIL: 1, VISAGE: 2}


# Marque une commande d'afficheur comme un recouvrement temporaire, par
# opposition au choix de l'utilisateur.
RECOUVREMENT = "regle"

# Rang d'un ordre d'actionneur, quand plusieurs regles visent le meme.
#
# L'ARRET demande par une regle ACTIVE l'emporte toujours : une
# protection battue par une demande de marche ne protege rien. C'est le
# pendant de PREPONDERANCE pour ce qui s'allume, a ceci pres que le
# critere n'est pas QUI demande mais CE QUI est demande.
#
# Avant ces rangs, c'etait la derniere regle traitee qui gagnait, donc
# l'ordre de `GRANDEURS`. « Trop de soleil, eteins la lampe » posee sur
# la luminosite perdait contre « budget non atteint, allume la lampe »
# posee sur l'eclairement du jour, traite apres -- la lampe s'allumait
# en plein soleil. Le meme montage sur la pompe marchait, par chance :
# le niveau d'eau est traite apres l'humidite du sol.
#
# L'ordre de `GRANDEURS` ne departage donc plus que des rangs EGAUX, et
# seulement pour savoir quelle regle le journal citera.
RANG_REPOS, RANG_MARCHE, RANG_ARRET = 0, 1, 2


class Jugement(NamedTuple):
    """Ce que le reseau pense d'une grandeur."""
    bas: bool
    haut: bool


class Commande(NamedTuple):
    valeur: float
    # Qui a decide : "seuil", "visage" ou "manuel". Le journal le garde,
    # et l'ecran le montre -- « le bipeur s'est declenche a cause d'un
    # seuil » ne se relit pas comme « a cause d'un visage ».
    source: str
    # Texte a afficher, pour le seul afficheur.
    texte: str | None = None
    # Afficheurs seulement : marque un recouvrement, qu'on pose ou qu'on
    # leve. Le lever ne l'eteint pas -- il lui rend ce qu'il montrait.
    priorite: str | None = None


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


def _appliquer(ordres: dict, rangs: dict, affichages: dict,
               action: Action | None, actif: bool, origine: str) -> None:
    """Traduit une action, et l'etat de son declencheur, en ordre.

    Le SEUL endroit qui sache ce que declencher veut dire. Les bornes et
    les visages y passent tous les deux : c'est ce qui garantit qu'une
    action se comporte pareil, quelle que soit la raison qui l'a
    reveillee.

    `rangs` retient, par actionneur, la force de l'ordre deja retenu --
    voir RANG_ARRET. Il ne sort pas d'ici : seuls les ordres comptent
    pour l'appelant.
    """
    if action is None or action.genre == "aucun":
        return

    if action.genre == "ecran":
        cible = action.cible or "ecran"
        gagnant = affichages.get(cible, (0, None, origine))
        if actif and PREPONDERANCE[origine] > gagnant[0]:
            affichages[cible] = (PREPONDERANCE[origine], action, origine)
        elif cible not in affichages:
            # L'afficheur est cite par une regle sans que rien ne le
            # demande : on le note quand meme, pour penser a LEVER le
            # recouvrement. Sans cela l'ecran garderait pour toujours le
            # dernier message d'une regle depuis relachee.
            affichages[cible] = gagnant
        return

    if action.genre == "actionneur" and action.cible:
        vise = float(action.valeur or 0.0)

        if actif:
            voulu, rang = vise, (RANG_ARRET if vise == 0.0 else RANG_MARCHE)
        elif vise > 0:
            # Une action « Allumer » relachee rend l'actionneur a
            # l'arret : sans cela, un bipeur declenche par un reservoir
            # vide sonnerait encore une fois rempli.
            voulu, rang = 0.0, RANG_REPOS
        else:
            # Une action « Eteindre » relachee ne demande RIEN, et c'est
            # tout l'interet d'une protection : tant que la borne n'est
            # pas franchie, elle laisse les autres regles decider.
            #
            # On l'inversait autrefois en « allumer », par symetrie avec
            # le cas precedent. Une protection devenait alors un ordre
            # de marche : « si l'eau est basse, coupe la pompe » mettait
            # la pompe en route tout le reste du temps.
            return

        # A rang egal, le premier arrive garde la main -- la valeur est
        # de toute facon la meme, seule change la regle que le journal
        # citera.
        if rang > rangs.get(action.cible, -1):
            rangs[action.cible] = rang
            ordres[action.cible] = Commande(voulu, origine)


def _declenchements(regles: dict[str, Regle],
                    franchis: dict[str, str | None],
                    regles_visages: dict[str, Action],
                    presents: set[str]):
    """Chaque action reglee par l'utilisateur, avec son etat du moment.

    Les bornes d'abord, les visages ensuite. Cet ordre ne decide plus de
    rien : deux regles actives sur le meme actionneur se departagent par
    leur RANG (voir RANG_ARRET), et l'ordre ne tranche plus que des
    rangs egaux -- qui demandent de toute facon la meme chose.
    """
    for grandeur in GRANDEURS:
        regle = regles.get(grandeur)
        if regle is None:
            continue
        yield regle.action_bas, franchis.get(grandeur) == "bas", SEUIL
        yield regle.action_haut, franchis.get(grandeur) == "haut", SEUIL

    for sujet, action in regles_visages.items():
        yield action, devant(sujet, presents), VISAGE


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
    # Par actionneur : la force de l'ordre retenu, pour qu'un arret
    # demande ne soit pas ecrase par une demande de marche.
    rangs: dict[str, int] = {}
    # Par afficheur : le message qui l'emporte, son rang et son origine.
    # Un rang de zero signifie qu'aucune regle ne demande rien en ce
    # moment -- il faudra alors lever le recouvrement.
    affichages: dict[str, tuple[int, Action | None, str]] = {}

    for action, actif, origine in _declenchements(regles, franchis,
                                                  regles_visages or {},
                                                  presents or set()):
        _appliquer(ordres, rangs, affichages, action, actif, origine)

    for cible, (_, action, origine) in affichages.items():
        # Poser le recouvrement, ou le lever. Le lever n'eteint pas
        # l'ecran : il lui rend ce qu'il montrait avant.
        ordres[cible] = (Commande(1.0, origine, action.texte, RECOUVREMENT)
                         if action is not None
                         else Commande(0.0, origine, None, RECOUVREMENT))

    return ordres
