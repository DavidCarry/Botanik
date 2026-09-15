# Botanik

Serre à lentilles automatisée. Des capteurs mesurent l'ambiance, un
dashboard l'affiche, et un réseau de neurones entraîné pour l'occasion
décide de l'arrosage et de l'éclairage.

Projet IoT / ML 2026 — Raspberry Pi 5, Debian 13.

## Comment ça tient ensemble

```
                 botanik/mesures/<capteur>
capteurs ──> publisher ──MQTT──> collecteur ──> PostgreSQL
                                                     │
                        navigateur <── API ──────────┘
                             │
                             │   botanik/commandes/<actionneur>
                             └──────MQTT──────> actionneurs ──> relais
                                 <─────MQTT─────┘
                                  botanik/etat/<actionneur>
```

Le navigateur reçoit les mesures **poussées** par l'API, qui relaie ce
qu'elle lit sur `botanik/mesures/#` — un flux `text/event-stream` sur
`/api/flux`. Les courbes, elles, continuent d'interroger la base : un
historique agrégé se calcule, une valeur du moment n'a qu'à arriver vite.

Trois topics, trois sens. Le dernier est celui qui rend l'ecran honnete :
l'interrupteur affiche l'etat que l'actionneur a **annonce**, pas celui
qu'on lui a demande. Une pompe en panne ne ressemble donc plus a une
pompe qui tourne.

Quatre processus, volontairement séparés :

| Composant | Rôle | Peut tomber sans entraîner les autres |
|---|---|---|
| `publisher.py` | lit les capteurs, publie sur MQTT | oui |
| `collecteur.py` | écoute MQTT, archive en base | oui |
| `actionneurs.py` | écoute les commandes, actionne, annonce l'état | oui |
| `main.py` | API HTTP + service du dashboard | oui |
| broker + base | conteneurs Docker | non |

Le découplage vient de MQTT : le publisher ne sait pas qui l'écoute, le
collecteur ne sait pas qui publie. Ajouter un consommateur — le modèle,
plus tard — ne demande de toucher à aucun des deux.

## Arborescence

```
backend/
  main.py          API HTTP, et service du frontend compilé
  publisher.py     lecture des capteurs -> MQTT
  collecteur.py    MQTT -> PostgreSQL
  actionneurs.py   MQTT -> relais, et retour d'état
  bus.py           liaison MQTT de l'API (émet, et écoute les états)
  service.py       ossature commune aux services MQTT
  registre.py      lecture des deux registres
  capteurs.yaml    ce qui est mesuré : plages, échelles, comment le lire
  actionneurs.yaml ce qui est piloté : broches, comment l'actionner
  auth.py          comptes et sessions
  systeme.py       état de la machine (CPU, mémoire, disque)
  drivers/         un module par type de sonde
frontend/
  src/composants/  interface React
  src/styles/      jetons de design (couleurs, typographie, rayons)
infra/
  postgres/        schéma initial
  mosquitto/       configuration du broker
  systemd/         unités de service + installateur
```

`capteurs.yaml` et `actionneurs.yaml` sont la source unique de vérité.
Chaque entrée y déclare **deux** façons d'être manipulée : le matériel
réel, et une simulation. La variable `MODE` (`faux` | `reel`) choisit
laquelle s'applique — ce qui permet de développer toute la chaîne sans
une seule sonde branchée, et de basculer en démonstration si un
composant lâche.

## Démarrer

Prérequis : Docker, Python 3.13, Node 22.

```bash
infra/initialiser-secrets.sh         # mot de passe MQTT, tiré au hasard
docker compose up -d                 # broker MQTT + PostgreSQL

python -m venv backend/.venv         # dépendances Python
backend/.venv/bin/pip install -r backend/requirements.txt

cd frontend && npm install && npm run build && cd ..

./demarrer.sh                        # lance les trois services
```

Le dashboard répond sur `http://localhost:8000`. Au premier démarrage, un
compte est créé et son mot de passe s'affiche **une seule fois** dans
`logs/api.log`.

En développement, `npm run dev` sert le front sur `:5173` avec
rechargement à chaud ; les appels `/api` sont proxifiés vers `:8000`.

| Commande | Effet |
|---|---|
| `./demarrer.sh` | lance tout |
| `./demarrer.sh etat` | ce qui tourne |
| `./demarrer.sh arreter` | coupe tout |
| `./sauvegarder.sh` | archive la base dans `sauvegardes/` |

## Sur la Raspberry Pi

```bash
infra/systemd/installer.sh   # une fois : les services redémarrent seuls
./deployer.sh                # ensuite : à chaque mise à jour
```

`deployer.sh` ne refait que le nécessaire : modifier un fichier Python ne
déclenche pas une reconstruction du frontend.

## Choix à connaître

- **Pas de nginx.** Uvicorn sert l'API *et* le frontend compilé. Une
  machine, un port, un processus de moins à surveiller.
- **Sessions en base, pas de JWT.** Un seul serveur ici, et un jeton
  stocké se révoque — ce qu'un JWT ne sait pas faire sans machinerie.
- **Cookie `httponly`.** Le jeton reste hors de portée du JavaScript de
  la page.
- **Agrégation côté SQL** (`date_bin`). Un mois de mesures à la minute
  ferait 43 000 points pour quelques centaines de pixels.
- **Poussée pour l'instantané, interrogation pour l'historique.** Les
  bulles reçoivent chaque mesure à l'instant où elle est publiée ;
  interroger l'API ajoutait jusqu'à cinq secondes de retard pour une
  valeur qui n'a rien à calculer. SSE plutôt que WebSocket : les mesures
  ne circulent que dans un sens, et `EventSource` se reconnecte seul.
  Plutôt qu'un client MQTT dans le navigateur, aussi : il aurait fallu
  livrer le mot de passe du broker à la page.
- **127.0.0.1 plutôt que `localhost`** dans les URL de service. Ce nom
  résout `::1` avant `127.0.0.1`, et Docker ne publie ces ports que sur
  IPv4 : chaque connexion perdait deux secondes à échouer en IPv6 avant
  de retomber sur IPv4.
- **Le schéma d'authentification se crée au démarrage**, pas dans
  `init.sql` : ce dernier n'est joué qu'à la création du volume, donc
  jamais sur une base déjà en place.
- **L'état des actionneurs est retenu par le broker**, pas stocké en
  base. C'est une valeur courante, pas un historique : les messages
  `retain` la restituent en quelques millisecondes à toute API qui
  redémarre. L'historique des ordres, lui, est dans la table `commandes`.
- **La commande part sur MQTT avant d'être écrite en base.** `commandes`
  est ainsi le journal de ce qui a réellement été émis, et non de ce
  qu'on a souhaité.

## Pannes silencieuses

Une panne qui se voit se répare. Le projet doit tourner plusieurs
semaines sans surveillance, et c'est la base qui portera l'historique de
germination et le jeu de données du modèle : une interruption passée
inaperçue pendant trois jours serait irrattrapable.

| Composant | Symptôme à l'écran |
|---|---|
| Actionneur | l'interrupteur refuse de bouger, « n'a pas répondu » |
| PostgreSQL | bulles vides, courbe vide |
| API | la page ne charge plus |
| **Collecteur** | l'indicateur passe à **« Archivage arrêté »** |
| **Un capteur isolé** | **sa bulle s'éteint**, la dernière valeur reste lisible |
| **Sauvegarde** | son âge s'affiche dans le panneau Machine |

Les trois derniers ne se voyaient pas. Le premier est devenu invisible en
passant les bulles au flux MQTT : elles continuaient de défiler alors que
plus rien n'était enregistré.

Deux mécanismes, parce que ce sont deux natures de panne :

- **La chaîne entière** se juge côté serveur (`/api/sante`) : âge de la
  dernière mesure *archivée*, comparé à l'horloge de la machine qui
  écrit. Un téléphone mal réglé donnerait sinon de fausses alertes.
- **Un capteur isolé** se juge côté navigateur, en comparant les capteurs
  *entre eux* : celui qui accuse plus d'une minute de retard sur le plus
  récent s'est tu. Aucune horloge n'intervient. Et si tous se taisent,
  aucun n'est en retard sur les autres — c'est alors la chaîne qui est en
  cause, et c'est l'autre indicateur qui parle.

## Sécurité

Ce qui est en place :

- mots de passe hachés en **scrypt** avec sel aléatoire, comparaison à
  temps constant ; sessions en jetons aléatoires révocables ;
  cookie `httponly` + `samesite=lax` (qui couvre aussi le CSRF)
- **toutes** les requêtes SQL sont paramétrées
- **le broker MQTT refuse les anonymes.** Sans cela, n'importe qui sur le
  réseau pouvait démarrer la pompe ou injecter de fausses mesures que le
  collecteur aurait archivées — et dont le modèle aurait appris. Le mot
  de passe est tiré au hasard par `infra/initialiser-secrets.sh`, vit
  dans `.env`, et ne figure pas dans le dépôt
- **PostgreSQL n'écoute que sur la boucle locale.** Les services tournent
  sur la même machine ; une base ouverte au réseau se lisait et
  s'effaçait depuis n'importe quel poste
- **sauvegarde quotidienne** de la base, 14 jours d'historique

Ce qui ne l'est pas, et pourquoi :

- **pas de HTTPS.** Réseau local isolé, aucune exposition Internet. Un
  certificat auto-signé afficherait un avertissement du navigateur à
  chaque démonstration pour un gain nul dans ce contexte. À reprendre si
  l'installation devait sortir du LAN.
- **pas de limite sur les tentatives de connexion.** Un seul compte, un
  réseau local, et le risque principal serait de se bloquer soi-même.
- **le port MQTT reste ouvert au réseau**, mais authentifié : un client
  externe doit pouvoir s'y connecter pour une démonstration.

## État

Fait : les deux boucles complètes — capteurs → écran, et écran →
actionneurs → écran — authentification, déploiement automatisé sur la Pi,
sauvegarde quotidienne.

Reste : le matériel (rien n'est acheté, tout tourne en `MODE=faux`) et le
réseau de neurones. Ni l'un ni l'autre ne demande de toucher à
l'architecture : un driver à écrire dans `drivers/` pour le premier, un
publieur de plus sur `botanik/commandes/` — avec `source: "ia"` — pour le
second.
