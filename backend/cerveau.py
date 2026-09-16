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
from datetime import datetime, timezone

import numpy as np
import psycopg

import decision
import donnees
import eclairement
import poids as magasin
import registre
import reseau
import service
from config import (
    DB_URL, TOPIC_ALERTES, TOPIC_COMMANDES, TOPIC_ETAT, TOPIC_MESURES,
)

# Cadence de decision. L'humidite d'un sol ne change pas en cinq secondes ;
# decider plus souvent ne ferait qu'agiter les actionneurs.
DECISION_S = 30

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

    # ---- modele ----

    def relire_modele(self):
        try:
            with psycopg.connect(DB_URL, connect_timeout=5) as conn:
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
        identifiant = msg.topic.rsplit("/", 1)[-1]
        try:
            charge = json.loads(msg.payload)
        except json.JSONDecodeError:
            return
        if msg.topic.startswith(TOPIC_ETAT):
            self.etats[identifiant] = float(charge.get("valeur", 0))
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

        try:
            with psycopg.connect(DB_URL, connect_timeout=5) as conn:
                contexte["eclairement_jour"] = eclairement.heures_du_jour(conn)
        except psycopg.Error as e:
            self._plaindre(f"eclairement du jour indisponible : {e}")
            return None

        local = datetime.now()
        contexte["heure"] = local.hour + local.minute / 60

        X = np.array([[contexte[e] for e in donnees.ENTREES]], dtype=float)
        return X, contexte

    # ---- sortie ----

    def ordonner(self, client, actionneur, valeur, source):
        """N'emet que si l'actionneur n'est pas deja dans cet etat.

        L'etat vient de l'actionneur lui-meme, pas d'un souvenir local :
        si son service redemarre et repart a zero, la divergence est vue
        au tour suivant et corrigee.
        """
        if self.etats.get(actionneur) == valeur:
            return
        charge = {"valeur": valeur, "source": source,
                  "ts": datetime.now(timezone.utc).isoformat()}
        client.publish(f"{TOPIC_COMMANDES}/{actionneur}", json.dumps(charge), qos=1)
        print(f"{source} -> {actionneur} = {valeur}", flush=True)

    # ---- boucle ----

    def annoncer_alertes(self, client, jugements, contexte):
        """Publie ce qui ne va pas, et seulement quand cela change.

        Message retenu : un service qui se connecte ensuite connait
        immediatement les alertes en cours, sans avoir a interroger qui
        que ce soit.

        Une alerte reste ouverte meme quand la serre est en train d'y
        remedier -- la pompe tourne, mais le sol est encore trop sec.
        C'est precisement ce qu'on veut voir a l'ecran : le probleme, et
        le fait qu'il soit pris en charge.
        """
        for grandeur, cote in decision.alertes(jugements).items():
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

    def decider(self, client):
        """Met a jour les etats voulus. N'actionne rien : c'est `tour` qui
        traduit ces etats en impulsions et en salves."""
        if self.poids is None:
            return
        situation = self.situation()
        if situation is None:
            return
        X, contexte = situation

        juges = reseau.predire(self.poids, donnees.normaliser(X, self.bornes))[0]
        jugements = {
            grandeur: decision.Jugement(
                bool(juges[donnees.SORTIES.index(f"{grandeur}_bas")]),
                bool(juges[donnees.SORTIES.index(f"{grandeur}_haut")]),
            )
            for grandeur in decision.GRANDEURS
        }

        self.voulu = decision.decider(jugements, contexte)
        self.annoncer_alertes(client, jugements, contexte)
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

        # Etats maintenus : ils suivent la decision sans mise en forme.
        for actionneur in ("ventilation", "lumiere"):
            ordre = self.voulu.get(actionneur)
            if ordre:
                self.ordonner(client, actionneur, ordre.valeur, ordre.source)

        self._pompe(client, maintenant)
        self._bipeur(client, maintenant)

    def _pompe(self, client, maintenant):
        """Impulsion puis repos : on laisse l'eau s'infiltrer avant de
        juger a nouveau, sinon on noierait les graines."""
        ordre = self.voulu.get("pompe")
        if ordre is None:
            return

        if self.fin_impulsion is not None:
            if maintenant >= self.fin_impulsion:
                self.ordonner(client, "pompe", 0.0, "ia")
                self.fin_impulsion = None
                self.repos_jusqu_a = maintenant + REPOS_S
            return

        if ordre.valeur > 0 and maintenant >= self.repos_jusqu_a:
            self.ordonner(client, "pompe", 1.0, ordre.source)
            self.fin_impulsion = maintenant + IMPULSION_S
        elif ordre.valeur == 0:
            # Couvre le cas de la securite : couper meme hors impulsion.
            self.ordonner(client, "pompe", 0.0, ordre.source)

    def _bipeur(self, client, maintenant):
        """Salves tant que l'alerte tient."""
        ordre = self.voulu.get("bipeur")
        if ordre is None or ordre.valeur == 0:
            self.ordonner(client, "bipeur", 0.0, "ia")
            return
        if maintenant < self.bascule_bip:
            return
        actif = self.etats.get("bipeur", 0.0) > 0
        self.ordonner(client, "bipeur", 0.0 if actif else 1.0, "ia")
        self.bascule_bip = maintenant + (SILENCE_BIP_S if actif else BIP_S)


def main():
    c = Cerveau()
    pilotes = [a["id"] for a in registre.actionneurs_actifs()
               if a.get("pilote") == "ia"]

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f"Connexion MQTT refusee : {reason_code}", flush=True)
            return
        client.subscribe(f"{TOPIC_MESURES}/#", qos=0)
        client.subscribe(f"{TOPIC_ETAT}/#", qos=1)
        print("Abonne aux mesures et aux etats", flush=True)

    print(f"Cerveau : {len(pilotes)} actionneurs pilotes "
          f"({', '.join(pilotes)}), decision toutes les {DECISION_S}s",
          flush=True)
    service.executer("Cerveau", periode=1, travail=c.tour,
                     on_connect=on_connect, on_message=c.sur_message)


if __name__ == "__main__":
    main()
