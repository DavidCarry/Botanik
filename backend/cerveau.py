"""Le modele aux commandes.

Ecoute les mesures sur MQTT, decide, et publie sur le meme topic que le
pilotage manuel -- avec `source: "ia"` au lieu de `"manuel"`. Rien d'autre
dans la chaine ne sait qui a decide, et c'est voulu : le modele n'est
qu'un emetteur de plus.

Il lit ses poids en base au demarrage et les relit periodiquement : un
reentrainement prend effet sans redemarrer le service.
"""

import json
import time
from datetime import datetime, timezone

import numpy as np
import psycopg

import donnees
import poids as magasin
import reseau
import service
from config import DB_URL, TOPIC_COMMANDES, TOPIC_ETAT, TOPIC_MESURES

# Cadence de decision. L'humidite d'un sol ne change pas en cinq secondes ;
# decider plus souvent ne ferait qu'agiter les actionneurs.
DECISION_S = 30

# Arrosage par impulsion, comme l'annonce le registre : « 20 mL par
# impulsion ». Une pompe maintenue allumee autour du seuil de decision
# battrait sans arret et noierait les graines. La duree correspond au
# debit de la pompe reelle, a recalibrer quand elle sera branchee.
IMPULSION_S = 4
REPOS_S = 180

# Sans mesure fraiche, on ne decide pas : mieux vaut ne rien faire que
# d'agir sur une valeur d'il y a une heure.
FRAICHEUR_S = 120

RELECTURE_MODELE_S = 300


class Cerveau:
    def __init__(self):
        self.mesures: dict[str, tuple[float, float]] = {}   # id -> (valeur, instant)
        self.etats: dict[str, float] = {}
        self.poids = None
        self.bornes = None
        self.version = None
        self.prochaine_decision = 0.0
        self.prochaine_relecture = 0.0
        self.fin_impulsion = None
        self.repos_jusqu_a = 0.0
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
                  f"(exactitude {meta['metriques']['exactitude_test']})", flush=True)
        self.poids, self.bornes, self.version = p, np.array(meta["bornes"]), version

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

    def entree(self) -> np.ndarray | None:
        """Les quatre mesures, dans l'ordre attendu par le reseau, ou None
        s'il en manque une ou si l'une d'elles a vieilli."""
        maintenant = time.monotonic()
        valeurs = []
        for capteur in donnees.ENTREES:
            connue = self.mesures.get(capteur)
            if connue is None or maintenant - connue[1] > FRAICHEUR_S:
                self._plaindre(f"en attente d'une mesure fraiche de {capteur}")
                return None
            valeurs.append(connue[0])
        return np.array([valeurs], dtype=float)

    # ---- sortie ----

    def ordonner(self, client, actionneur: str, valeur: float):
        """N'emet que si l'actionneur n'est pas deja dans cet etat.

        L'etat vient de l'actionneur lui-meme, pas d'un souvenir local :
        si son service redemarre et repart a zero, la divergence est vue
        au tour suivant et corrigee.
        """
        if self.etats.get(actionneur) == valeur:
            return
        charge = {"valeur": valeur, "source": "ia",
                  "ts": datetime.now(timezone.utc).isoformat()}
        client.publish(f"{TOPIC_COMMANDES}/{actionneur}", json.dumps(charge), qos=1)
        print(f"ia -> {actionneur} = {valeur}", flush=True)

    # ---- boucle ----

    def decider(self, client):
        X = self.entree()
        if X is None or self.poids is None:
            return

        action = int(reseau.predire(self.poids, donnees.normaliser(X, self.bornes))[0])
        eau = X[0][donnees.ENTREES.index("niveau_eau")]

        # Garde-fou en dur, hors du reseau. Le modele a appris cette regle,
        # mais un modele se trompe parfois et une pompe qui tourne a sec
        # est perdue.
        if action == donnees.ARROSER and eau < donnees.RESERVE_MINIMALE:
            self._plaindre(f"arrosage refuse : reserve a {eau:.0f} %")
            action = donnees.RIEN

        if action == donnees.ARROSER:
            if time.monotonic() >= self.repos_jusqu_a:
                self.ordonner(client, "pompe", 1.0)
                self.fin_impulsion = time.monotonic() + IMPULSION_S
            self.ordonner(client, "ventilation", 0.0)
        elif action == donnees.VENTILER:
            self.ordonner(client, "ventilation", 1.0)
        else:
            self.ordonner(client, "ventilation", 0.0)

        self.plainte = None

    def tour(self, client):
        maintenant = time.monotonic()

        if self.fin_impulsion and maintenant >= self.fin_impulsion:
            self.ordonner(client, "pompe", 0.0)
            self.fin_impulsion = None
            # Laisser l'eau s'infiltrer avant de juger a nouveau : arroser
            # de nouveau tout de suite reviendrait a noyer les graines.
            self.repos_jusqu_a = maintenant + REPOS_S

        if maintenant >= self.prochaine_relecture:
            self.relire_modele()
            self.prochaine_relecture = maintenant + RELECTURE_MODELE_S

        if maintenant >= self.prochaine_decision:
            self.decider(client)
            self.prochaine_decision = maintenant + DECISION_S


def main():
    c = Cerveau()

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f"Connexion MQTT refusee : {reason_code}", flush=True)
            return
        client.subscribe(f"{TOPIC_MESURES}/#", qos=0)
        client.subscribe(f"{TOPIC_ETAT}/#", qos=1)
        print("Abonne aux mesures et aux etats", flush=True)

    print(f"Cerveau : decision toutes les {DECISION_S}s, "
          f"impulsion {IMPULSION_S}s, repos {REPOS_S}s", flush=True)
    service.executer("Cerveau", periode=1, travail=c.tour,
                     on_connect=on_connect, on_message=c.sur_message)


if __name__ == "__main__":
    main()
