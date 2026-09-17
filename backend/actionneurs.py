"""Ecoute les commandes sur MQTT et actionne le materiel.

Miroir exact de publisher.py : celui-la lit le monde et le publie,
celui-ci ecoute des ordres et agit dessus. Il ne connait aucun actionneur
en particulier -- il parcourt le registre et appelle le driver indique.

Apres chaque action, il republie l'etat ATTEINT sur botanik/etat/<id>.
C'est ce qui separe un interrupteur qui affiche ce qu'il croit d'un
interrupteur qui affiche ce qui est : l'ecran n'attend plus sa propre
supposition, il attend la reponse du materiel.
"""

import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

import registre
import service
from config import MODE, TOPIC_COMMANDES, TOPIC_ETAT, TOPIC_MESURES
from drivers import SORTIES

# Largeur de l'afficheur : au-dela, on coupe plutot que de deborder.
COLONNES = 16

# Ce que chaque actionneur porteur de texte doit montrer, tel que
# l'utilisateur l'a demande. C'est une INTENTION -- « la temperature » --
# et non un texte fige : la valeur affichee doit suivre la mesure.
#
# C'est le fond, celui qui reste quand rien d'autre ne parle.
_contenu: dict[str, dict] = {}

# Ce qu'une regle pose PAR-DESSUS, le temps qu'elle dure : un reservoir
# vide, quelqu'un devant la camera. Une couche a part, et non un
# remplacement -- c'est elle qui permet a l'ecran de retrouver tout seul
# ce qu'il montrait quand la regle se releve.
#
# Le classement entre plusieurs messages -- une personne passe avant une
# alarme -- est fait en amont, par le cerveau. Ici il n'y a que
# « recouvert » ou « pas recouvert ».
_recouvrement: dict[str, dict] = {}

# L'allumage demande hors recouvrement, a retrouver quand celui-ci se
# leve : lever un recouvrement ne doit pas eteindre un ecran que
# l'utilisateur avait allume, ni allumer celui qu'il avait eteint.
_allumage: dict[str, float] = {}

# Dernieres mesures recues, pour composer ce texte. Le service s'abonne
# aux mesures uniquement pour cela.
_mesures: dict[str, dict] = {}

# Libelles des capteurs, lus une fois au registre.
_libelles: dict[str, str] = {}

# Dernier texte compose par actionneur, pour ne reecrire qu'au changement.
_lignes: dict[str, list[str]] = {}

# Dernier etat applique, pour rafraichir un afficheur sans le rallumer.
_etats: dict[str, float] = {}

# Actionneurs actuellement pilotes en simulation faute de materiel qui
# repond, pour n'annoncer que les bascules.
_en_repli: set[str] = set()


# Duree d'affichage de chaque mesure quand l'ecran en montre plusieurs.
#
# Cinq secondes : le temps de lire deux lignes sans avoir a attendre.
# Plus court, on rate la valeur ; plus long, on croit l'ecran fige.
DEFILEMENT_S = 5.0


def _une_mesure(capteur: str) -> list[str]:
    libelle = _libelles.get(capteur, capteur or "?")
    mesure = _mesures.get(capteur)
    if mesure is None:
        return [libelle, "en attente"]
    return [libelle, f"{mesure['valeur']} {mesure.get('unite', '')}".strip()]


def capteurs_choisis(contenu: dict) -> list[str]:
    """Les capteurs demandes, qu'il y en ait un ou plusieurs.

    L'ancien format ne portait qu'un `capteur`; on l'accepte toujours,
    sinon une regle enregistree avant ce changement cesserait d'afficher
    quoi que ce soit.
    """
    plusieurs = contenu.get("capteurs")
    if isinstance(plusieurs, list) and plusieurs:
        return [c for c in plusieurs if isinstance(c, str)]
    seul = contenu.get("capteur")
    return [seul] if seul else []


def affiche(actionneur: str) -> dict | None:
    """Ce qui doit etre a l'ecran : le recouvrement s'il y en a un, le
    choix de l'utilisateur sinon."""
    return _recouvrement.get(actionneur) or _contenu.get(actionneur)


def composer(contenu: dict) -> list[str]:
    """Les deux lignes a afficher, d'apres l'intention et les mesures.

    Composer ici plutot que dans le driver : le service connait le
    registre et recoit les mesures, le driver ne connait qu'un ecran.

    Plusieurs mesures demandees : elles defilent, chacune son tour. Le
    rang se calcule sur l'horloge et non sur un compteur -- ainsi deux
    ecrans afficheraient la meme chose au meme instant, et un service
    qui redemarre ne repart pas du debut.
    """
    if contenu.get("mode") == "texte":
        texte = str(contenu.get("texte", ""))
        return [texte[:COLONNES], texte[COLONNES:2 * COLONNES]]

    choisis = capteurs_choisis(contenu)
    if not choisis:
        return ["", ""]
    if len(choisis) == 1:
        return _une_mesure(choisis[0])

    rang = int(time.monotonic() / DEFILEMENT_S) % len(choisis)
    return _une_mesure(choisis[rang])


def charger_actionneurs():
    """Les actionneurs actifs, chacun avec le driver qui l'actionnera."""
    return registre.resoudre(registre.actionneurs_actifs(), SORTIES)


def annoncer(client: mqtt.Client, actionneur: str, valeur: float, **extras):
    """Publie l'etat d'un actionneur, en message retenu.

    `retain=True` est essentiel : le broker garde le dernier etat de
    chaque actionneur et le sert immediatement a tout nouvel abonne.
    Sans cela, une API qui redemarre ne saurait plus si la pompe tourne
    avant la prochaine commande -- et l'ecran resterait aveugle.
    """
    charge = {
        "valeur": valeur,
        "ts": datetime.now(timezone.utc).isoformat(),
        **extras,
    }
    client.publish(f"{TOPIC_ETAT}/{actionneur}", json.dumps(charge),
                   qos=1, retain=True)


def main():
    actionneurs = charger_actionneurs()
    if not actionneurs:
        print("Aucun actionneur actif dans actionneurs.yaml", flush=True)
        return

    _libelles.update({c["id"]: c["libelle"] for c in registre.capteurs_actifs()})
    premier = next(iter(_libelles), "")

    def actionner(client, actionneur, valeur):
        """Applique un etat et annonce ce qui a ete atteint.

        L'afficheur recoit en plus le texte a ecrire : c'est le seul
        actionneur dont l'etat ne se resume pas a allume ou eteint.
        """
        cible = actionneurs[actionneur]
        montre = affiche(actionneur)
        lignes = composer(montre) if montre else None

        # Meme principe que pour les capteurs : un materiel qui ne
        # repond plus ne fait pas disparaitre l'actionneur de l'ecran.
        # On accepte l'ordre en simulation, et la mention voyage avec
        # l'etat -- un interrupteur qui semble marcher alors que rien
        # n'est branche est pire qu'un interrupteur marque « simule ».
        simule = cible["source"] == "simule"
        try:
            atteint = SORTIES[cible["driver"]].appliquer(
                actionneur, valeur, cible["params"], lignes,
            )
            if actionneur in _en_repli:
                _en_repli.discard(actionneur)
                print(f"{actionneur} repond de nouveau", flush=True)
        except Exception as e:
            repli = cible.get("repli")
            if repli is None:
                raise
            if actionneur not in _en_repli:
                _en_repli.add(actionneur)
                print(f"{actionneur} ne repond pas ({e}) -- bascule sur "
                      f"la simulation", flush=True)
            atteint = SORTIES[repli["driver"]].appliquer(
                actionneur, valeur, repli["params"], lignes,
            )
            simule = True

        _etats[actionneur] = atteint
        if montre is None:
            annoncer(client, actionneur, atteint, simule=simule)
        else:
            _lignes[actionneur] = lignes
            # On annonce le contenu de FOND, pas le recouvrement : la page
            # de pilotage doit continuer a montrer ce que l'utilisateur a
            # choisi, qui ne change pas parce que quelqu'un passe devant
            # la camera. Les lignes, elles, disent ce qui est ecrit.
            annoncer(client, actionneur, atteint, simule=simule,
                     contenu=_contenu.get(actionneur), lignes=lignes)
        return atteint

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f"Connexion MQTT refusee : {reason_code}", flush=True)
            return
        client.subscribe(f"{TOPIC_COMMANDES}/#", qos=1)
        print(f"Abonne a {TOPIC_COMMANDES}/#", flush=True)

        # Au demarrage, tout est au repos : on l'annonce plutot que de
        # laisser l'ecran deviner. Un etat retenu d'une session
        # precedente serait devenu faux au redemarrage de la machine.
        # Les mesures ne servent qu'a nourrir l'afficheur.
        client.subscribe(f"{TOPIC_MESURES}/#", qos=0)

        # Au demarrage, tout est au repos : on l'annonce plutot que de
        # laisser l'ecran deviner.
        for actionneur in actionneurs:
            annoncer(client, actionneur, 0.0)

    def on_message(client, userdata, msg):
        identifiant = msg.topic.rsplit("/", 1)[-1]

        if msg.topic.startswith(TOPIC_MESURES):
            try:
                _mesures[identifiant] = json.loads(msg.payload)
            except json.JSONDecodeError:
                pass
            return

        actionneur = identifiant
        cible = actionneurs.get(actionneur)
        if cible is None:
            print(f"Commande ignoree : {actionneur} inconnu ou inactif",
                  flush=True)
            return

        try:
            charge = json.loads(msg.payload)
            valeur = float(charge["valeur"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            print(f"Commande illisible sur {msg.topic} : {e}", flush=True)
            return

        # Une commande peut porter ce qu'il faut afficher. On le retient :
        # l'intention survit a une extinction, et rallumer l'ecran le
        # remet sur la meme chose.
        if charge.get("priorite"):
            # Une regle pose ou leve un recouvrement. Elle ne touche pas
            # au choix de l'utilisateur, qui reparait dessous.
            nouveau = charge.get("contenu")
            if isinstance(nouveau, dict):
                _recouvrement[actionneur] = nouveau
            else:
                _recouvrement.pop(actionneur, None)
            # Un recouvrement allume ; sa levee rend l'ecran a l'etat
            # que l'utilisateur lui avait donne.
            valeur = (1.0 if actionneur in _recouvrement
                      else _allumage.get(actionneur, valeur))
        else:
            if isinstance(charge.get("contenu"), dict):
                _contenu[actionneur] = charge["contenu"]
            elif actionneur == "ecran" and actionneur not in _contenu:
                _contenu[actionneur] = {"mode": "mesure", "capteur": premier}
            _allumage[actionneur] = valeur

        try:
            atteint = actionner(client, actionneur, valeur)
        except Exception as e:
            # Un actionneur qui refuse ne doit pas emporter les autres :
            # on n'annonce simplement aucun etat, et l'ecran le montrera.
            print(f"Echec sur {actionneur} : {e}", flush=True)
            return

        print(f"{actionneur} -> {atteint}", flush=True)

    def suivre_mesures(client):
        """Garde l'afficheur a jour quand ce qu'il montre a change.

        Un ecran qui affiche « Temperature » doit suivre la temperature,
        pas figer celle de l'instant ou on l'a allume. On recompose donc
        a chaque tour, et on ne reecrit que si le texte differe.
        """
        for actionneur in set(_contenu) | set(_recouvrement):
            # Un afficheur eteint n'a rien a rafraichir -- et surtout, le
            # rafraichir ne doit jamais le rallumer.
            if actionneur not in actionneurs or not _etats.get(actionneur):
                continue
            montre = affiche(actionneur)
            if montre is None or composer(montre) == _lignes.get(actionneur):
                continue
            try:
                actionner(client, actionneur, _etats[actionneur])
            except Exception as e:
                print(f"Echec de rafraichissement sur {actionneur} : {e}", flush=True)

    for plainte in registre.collisions():
        print(f"ATTENTION cablage : {plainte}", flush=True)

    print(f"Actionneurs : mode {MODE}, {len(actionneurs)} pilotes", flush=True)
    service.executer(
        "Actionneurs", periode=1,
        travail=suivre_mesures,
        on_connect=on_connect, on_message=on_message,
    )


if __name__ == "__main__":
    main()
