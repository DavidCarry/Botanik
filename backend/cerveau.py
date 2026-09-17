"""Le modele aux commandes.

Ecoute les mesures sur MQTT, fait juger la situation au reseau, en deduit
les commandes par les regles de decision.py, et les publie sur le meme
topic que le pilotage manuel -- avec `source: "ia"` au lieu de
`"manuel"`. Rien d'autre dans la chaine ne sait qui a decide.

Trois responsabilites, trois modules :

  reseau + donnees   JUGENT    chaque grandeur est-elle trop basse, trop haute
  decision           DECIDE    que faire de ces jugements
  ce fichier         CADENCE   quand decider, combien de temps actionner

La cadence est ici et nulle part ailleurs parce qu'elle releve du temps :
une pompe s'actionne par impulsions, une alerte sonore par salves, et un
reseau n'a aucune notion de duree.
"""

import json
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import psycopg

import bdd
import decision
import donnees
import eclairement
import poids as magasin
import registre
import regles
import reseau
import seuils
import service
import verrous
from config import (
    TOPIC_ALERTES, TOPIC_COMMANDES, TOPIC_ETAT, TOPIC_MESURES, TOPIC_REGLES,
)

# Cadence de decision.
#
# Elle etait a trente secondes, au motif que l'humidite d'un sol ne
# change pas en cinq secondes. C'est vrai du sol -- et faux de la reserve
# d'eau, qu'on vide ou qu'on remplit en un geste. Le bipeur mettait
# jusqu'a une demi-minute a se declencher, puis autant a se taire, alors
# que l'ecran, lui, montrait le changement dans la demi-seconde.
#
# Decider vite ne fait plus battre les actionneurs depuis que les
# jugements ont une hysteresis : c'est elle qui empeche l'agitation, pas
# la lenteur.
DECISION_S = 2

# Le budget de lumiere du jour et les verrous poses a la main se lisent
# en BASE, et ils bougent lentement -- le cumul avance d'une seconde par
# seconde, un verrou dure cinq minutes. Les relire a chaque decision
# ouvrirait une connexion toutes les deux secondes pour rien.
CONTEXTE_LENT_S = 30

# Arrosage par impulsion, comme l'annonce le registre : 20 mL par
# impulsion. Une pompe maintenue allumee autour du seuil de decision
# battrait sans arret et noierait les graines. La duree correspond au
# debit de la pompe reelle, a recalibrer quand elle sera branchee.
IMPULSION_S = 4
REPOS_S = 180

# Alerte sonore par salves : un bipeur continu devient vite insupportable
# et plus personne n'y reagit. Une seconde toutes les huit se remarque
# sans s'imposer.
BIP_S = 1
SILENCE_BIP_S = 8

# Sans mesure fraiche, on ne decide pas : mieux vaut ne rien faire que
# d'agir sur une valeur d'il y a une heure.
FRAICHEUR_S = 120

RELECTURE_MODELE_S = 300

# Les entrees du reseau qui viennent reellement d'un capteur. Les deux
# autres -- l'eclairement du jour et l'heure -- se calculent.
CAPTEURS = [e for e in donnees.ENTREES if e not in donnees.HORS_REGISTRE]


class Cerveau:
    def __init__(self):
        self.mesures: dict[str, tuple[float, float]] = {}
        self.etats: dict[str, float] = {}
        self.poids = None
        self.bornes = None
        self.version = None
        self.voulu: dict[str, decision.Commande] = {}
        # Jugements du tour precedent : l'hysteresis a besoin de savoir
        # d'ou l'on vient pour decider si l'on bascule.
        self.jugements: dict[str, decision.Jugement] = {}
        # Actionneurs repris en main, et l'instant ou chacun se libere.
        self.verrous: dict[str, datetime] = {}
        # Dernier cote publie pour chaque grandeur, afin de n'emettre que
        # les changements. Vide au depart : la premiere decision publie
        # donc l'etat de toutes, ce qui donne au journal une base saine.
        self.alertes: dict[str, str | None] = {}
        self.prochaine_decision = 0.0
        self.prochaine_relecture = 0.0
        self.fin_impulsion = None
        self.repos_jusqu_a = 0.0
        self.bascule_bip = 0.0
        self.plainte = None
        # Les actionneurs que le registre lui confie. Un actionneur
        # retire du registre -- parce qu'il n'est pas encore livre --
        # ne doit pas continuer a recevoir des ordres que personne
        # n'ecoute : le journal se remplirait de commandes ignorees.
        self.pilotes: set[str] = set()
        # Les regles de l'utilisateur, l'etendue de chaque grandeur et les
        # seuils que le reseau a appris : de quoi resoudre une borne.
        self.regles: dict[str, decision.Regle] = {}
        self.etendues: dict[str, float] = {}
        self.seuils_ia: dict[str, dict] = {}
        # Cote franchi au tour precedent, pour l'hysteresis des bornes.
        self.franchis: dict[str, str | None] = {}
        # Actionneurs qui s'expriment par salves, d'apres le registre.
        self.salves: dict[str, dict] = {}
        self.bascules: dict[str, float] = {}
        self.seuils_a_relire = True
        # Grandeurs dont un episode d'alerte est encore ouvert en base.
        self.ouvertes: set[str] = set()
        # Ce qui vient de la base, et l'instant ou il faudra le relire.
        self.contexte_lent = None
        self.prochain_contexte = 0.0

    # ---- modele ----

    def relire_modele(self):
        try:
            with bdd.connexion() as conn:
                charge = magasin.charger(conn)
        except psycopg.Error as e:
            self._plaindre(f"base injoignable pour relire le modele : {e}")
            return
        if charge is None:
            self._plaindre("aucun modele en base -- lancer entrainer.py")
            return
        p, meta, version = charge
        if version != self.version:
            print(f"modele {version} charge "
                  f"({meta['metriques']['exactitude_test']} par jugement)",
                  flush=True)
        self.poids = p
        self.bornes = np.array(meta["bornes"])
        self.version = version

    def _plaindre(self, message):
        """Ne repete pas la meme plainte a chaque tour : un journal noye
        ne se lit plus."""
        if message != self.plainte:
            print(message, flush=True)
            self.plainte = message

    # ---- entrees ----

    def sur_message(self, client, userdata, msg):
        if msg.topic == TOPIC_REGLES:
            # On ne lit pas la base ici -- on est dans le fil de paho.
            # Il suffit de perimer le contexte : le prochain tour relira.
            self.prochain_contexte = 0.0
            print("regles modifiees, relecture au prochain tour", flush=True)
            return

        identifiant = msg.topic.rsplit("/", 1)[-1]
        try:
            charge = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        if msg.topic.startswith(TOPIC_ETAT):
            self.etats[identifiant] = float(charge.get("valeur", 0))
        elif msg.topic.startswith(TOPIC_COMMANDES):
            # Le verrou se pose des que la commande passe, sans attendre
            # la prochaine decision : entre les deux, ce fil maintient
            # l'etat voulu CHAQUE SECONDE et effacerait la reprise en
            # main avant meme qu'on ait lache l'interrupteur.
            if charge.get("source") == "manuel":
                self.verrous[identifiant] = (
                    datetime.now(timezone.utc)
                    + timedelta(seconds=decision.VERROU_MANUEL_S)
                )
                print(f"main reprise sur {identifiant}", flush=True)
        else:
            self.mesures[identifiant] = (float(charge["valeur"]), time.monotonic())

    def situation(self):
        """Les six entrees du reseau, ou None s'il manque une mesure.

        L'eclairement du jour se relit en base a chaque decision plutot
        que de s'entretenir en memoire : un service qui redemarre a midi
        retrouve ainsi le bon cumul au lieu de repartir de zero et de
        rallumer la lampe pour rien.
        """
        maintenant = time.monotonic()
        contexte = {}
        for capteur in CAPTEURS:
            connue = self.mesures.get(capteur)
            if connue is None or maintenant - connue[1] > FRAICHEUR_S:
                self._plaindre(f"en attente d'une mesure fraiche de {capteur}")
                return None
            contexte[capteur] = connue[0]

        # Une seule connexion pour les deux lectures : l'eclairement du
        # jour et les verrous poses par la main. Elle n'est rouverte que
        # toutes les CONTEXTE_LENT_S -- entre-temps on reutilise ce qu'on
        # a lu, qui n'a pas eu le temps de changer de sens.
        instant = time.monotonic()
        if self.contexte_lent is None or instant >= self.prochain_contexte:
            try:
                with bdd.connexion() as conn:
                    self.contexte_lent = (eclairement.heures_du_jour(conn),
                                          verrous.actifs(conn))
                    self.regles = regles.lire(conn)
                    # Les episodes encore ouverts en base. Le cerveau perd
                    # la memoire a chaque redemarrage ; sans cette
                    # relecture, une alerte ouverte avant l'arret -- ou
                    # par une regle depuis retiree -- resterait ouverte
                    # pour toujours, et l'ecran afficherait un probleme
                    # que plus personne ne surveille.
                    with conn.cursor() as cur:
                        cur.execute("SELECT grandeur FROM alertes "
                                    "WHERE fin IS NULL")
                        self.ouvertes = {g for (g,) in cur.fetchall()}
            except psycopg.Error as e:
                self._plaindre(f"lecture de la base impossible : {e}")
                return None
            self.prochain_contexte = instant + CONTEXTE_LENT_S
            # Les frontieres du reseau se relisent au meme rythme : elles
            # dependent de la chaleur et de la lumiere, qui ne changent
            # pas en deux secondes. Mais elles ont besoin du contexte
            # complet, qui n'est pret qu'en fin de methode.
            self.seuils_a_relire = True

        eclaire, journal = self.contexte_lent
        contexte["eclairement_jour"] = eclaire

        # Le journal fait foi, mais une commande a peine emise peut ne
        # pas encore y figurer : on garde le plus tardif des deux, et on
        # oublie ce qui a expire.
        maintenant = datetime.now(timezone.utc)
        for actionneur, fin in journal.items():
            if fin > self.verrous.get(actionneur, maintenant):
                self.verrous[actionneur] = fin
        self.verrous = {a: f for a, f in self.verrous.items() if f > maintenant}

        local = datetime.now()
        contexte["heure"] = local.hour + local.minute / 60

        if self.seuils_a_relire:
            self.relire_seuils(contexte)
            self.seuils_a_relire = False
        return contexte

    # ---- sortie ----

    def ordonner(self, client, actionneur, valeur, source, texte=None):
        """N'emet que si l'actionneur n'est pas deja dans cet etat.

        L'etat vient de l'actionneur lui-meme, pas d'un souvenir local :
        si son service redemarre et repart a zero, la divergence est vue
        au tour suivant et corrigee.

        Un actionneur repris en main est laisse tranquille, SAUF par la
        securite : si la reserve se vide pendant un arrosage manuel, la
        pompe s'arrete quand meme.
        """
        if actionneur not in self.pilotes:
            return
        if source != "securite" and actionneur in self.verrous:
            return
        if self.etats.get(actionneur) == valeur:
            return
        charge = {"valeur": valeur, "source": source,
                  "ts": datetime.now(timezone.utc).isoformat()}
        if texte is not None:
            charge["contenu"] = {"mode": "texte", "texte": texte}
        client.publish(f"{TOPIC_COMMANDES}/{actionneur}", json.dumps(charge), qos=1)
        print(f"{source} -> {actionneur} = {valeur}", flush=True)

    # ---- boucle ----

    def annoncer_alertes(self, client, franchis, contexte):
        """Publie ce qui ne va pas, et seulement quand cela change.

        Message retenu : un service qui se connecte ensuite connait
        immediatement les alertes en cours, sans avoir a interroger qui
        que ce soit.

        Une alerte reste ouverte meme quand la serre est en train d'y
        remedier -- la pompe tourne, mais le sol est encore trop sec.
        C'est precisement ce qu'on veut voir a l'ecran : le probleme, et
        le fait qu'il soit pris en charge.
        """
        # On parcourt aussi les grandeurs qu'on a deja signalees : une
        # regle retiree fait disparaitre sa grandeur de `franchis`, et
        # son alerte resterait ouverte pour toujours si personne ne
        # venait la fermer.
        a_examiner = (dict.fromkeys(franchis, None)
                      | dict.fromkeys(self.alertes, None)
                      | dict.fromkeys(self.ouvertes, None))
        for grandeur in a_examiner:
            cote = franchis.get(grandeur)
            if self.alertes.get(grandeur, "?") == cote:
                continue
            charge = {
                "cote": cote,
                "valeur": contexte.get(grandeur),
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            client.publish(f"{TOPIC_ALERTES}/{grandeur}", json.dumps(charge),
                           qos=1, retain=True)
            self.alertes[grandeur] = cote
            if cote:
                print(f"alerte {grandeur} {cote}", flush=True)
            else:
                print(f"alerte {grandeur} levee", flush=True)

    def relire_seuils(self, contexte):
        """Ou le reseau place ses frontieres, aux conditions du moment.

        Ce n'est plus lui qui commande, mais c'est toujours lui qui
        APPREND : une borne reglee sur « ia » le suit, et se deplace
        donc quand il fait chaud ou clair. Le balayage coute trop cher
        pour le refaire deux fois par seconde -- et ces frontieres
        bougent en minutes.
        """
        if self.poids is None:
            return
        try:
            self.seuils_ia = seuils.frontieres(self.poids, self.bornes, contexte)
        except Exception as e:
            self._plaindre(f"lecture des seuils impossible : {e}")

    def decider(self, client):
        """Confronte les mesures aux bornes, et en tire les ordres.

        Aucune regle n'est ecrite ici : tout vient de ce que
        l'utilisateur a regle. Une grandeur sans regle ne declenche ni
        alerte ni commande, et c'est l'etat de depart.
        """
        contexte = self.situation()
        if contexte is None:
            return

        franchis = decision.cotes_franchis(
            self.regles, contexte, self.seuils_ia, self.etendues, self.franchis,
        )
        self.franchis = franchis
        self.voulu = decision.decider(self.regles, franchis)
        self.annoncer_alertes(client, franchis, contexte)
        self.plainte = None

    def tour(self, client):
        maintenant = time.monotonic()

        if maintenant >= self.prochaine_relecture:
            self.relire_modele()
            self.prochaine_relecture = maintenant + RELECTURE_MODELE_S

        if maintenant >= self.prochaine_decision:
            self.decider(client)
            self.prochaine_decision = maintenant + DECISION_S

        if not self.voulu:
            return

        for actionneur, ordre in self.voulu.items():
            salve = self.salves.get(actionneur)
            if salve and ordre.valeur > 0:
                self._salve(client, actionneur, salve, maintenant)
            else:
                self.bascules.pop(actionneur, None)
                self.ordonner(client, actionneur, ordre.valeur, ordre.source,
                              ordre.texte)

    def _salve(self, client, actionneur, salve, maintenant):
        """Alterne allume et eteint tant que l'ordre tient.

        Un avertisseur continu devient vite insupportable, et plus
        personne n'y reagit. La cadence est declaree au registre, par
        actionneur : c'est une propriete du materiel, pas une regle de
        la serre.
        """
        if maintenant < self.bascules.get(actionneur, 0.0):
            return
        actif = self.etats.get(actionneur, 0.0) > 0
        self.ordonner(client, actionneur, 0.0 if actif else 1.0, "regle")
        repos = salve.get("repos_s", 8.0) if actif else salve.get("actif_s", 1.0)
        self.bascules[actionneur] = maintenant + float(repos)


def main():
    c = Cerveau()

    # Tout actionneur actif est pilotable par une regle : le registre ne
    # dit plus qui « appartient » a l'IA, puisqu'il n'y a plus de regles
    # ecrites en dur. C'est l'utilisateur qui designe les actionneurs, un
    # par un, dans les regles qu'il ecrit.
    actionneurs = registre.actionneurs_actifs()
    c.pilotes = {a["id"] for a in actionneurs}
    c.salves = {a["id"]: a["salve"] for a in actionneurs if a.get("salve")}

    # L'etendue de chaque grandeur, pour donner son echelle a la marge
    # d'hysteresis des bornes.
    connus = {x["id"]: x for x in registre.capteurs_actifs()}
    c.etendues = {}
    for grandeur in decision.GRANDEURS:
        if grandeur in connus:
            e = connus[grandeur]["echelle"]
            c.etendues[grandeur] = float(e["max"] - e["min"])
        elif grandeur in donnees.HORS_REGISTRE:
            bas, haut = donnees.HORS_REGISTRE[grandeur]
            c.etendues[grandeur] = float(haut - bas)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f"Connexion MQTT refusee : {reason_code}", flush=True)
            return
        client.subscribe(f"{TOPIC_MESURES}/#", qos=0)
        client.subscribe(f"{TOPIC_ETAT}/#", qos=1)
        client.subscribe(f"{TOPIC_COMMANDES}/#", qos=1)
        # L'API previent ici quand une regle change : sans cela, un
        # reglage fait a l'ecran attendrait la relecture periodique.
        client.subscribe(TOPIC_REGLES, qos=1)
        print("Abonne aux mesures, aux etats, aux commandes et aux regles",
              flush=True)

    print(f"Cerveau : {len(c.pilotes)} actionneurs a disposition "
          f"({', '.join(sorted(c.pilotes)) or 'aucun'}), decision toutes "
          f"les {DECISION_S}s", flush=True)
    print("  aucune regle n'est ecrite ici : tout vient de l'interface",
          flush=True)
    service.executer("Cerveau", periode=1, travail=c.tour,
                     on_connect=on_connect, on_message=c.sur_message)


if __name__ == "__main__":
    main()
