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
                            │        (FastAPI + React)
                            └──> API ──MQTT──> actionneurs
                    botanik/commandes/<actionneur>
```

Quatre processus, volontairement séparés :

| Composant | Rôle | Peut tomber sans entraîner les autres |
|---|---|---|
| `publisher.py` | lit les capteurs, publie sur MQTT | oui |
| `collecteur.py` | écoute MQTT, archive en base | oui |
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
  service.py       ossature commune aux deux services MQTT
  registre.py      lecture de capteurs.yaml
  capteurs.yaml    LE registre : ce qui existe, ses plages, comment le lire
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

`capteurs.yaml` est la source unique de vérité. Un capteur y déclare sa
plage favorable, son échelle d'affichage, et **deux** façons d'être lu :
le matériel réel, et une simulation plausible. La variable `MODE`
(`faux` | `reel`) choisit laquelle s'applique — ce qui permet de
développer l'interface sans une seule sonde branchée, et de basculer en
démonstration si une sonde lâche.

## Démarrer

Prérequis : Docker, Python 3.13, Node 22.

```bash
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
- **Le schéma d'authentification se crée au démarrage**, pas dans
  `init.sql` : ce dernier n'est joué qu'à la création du volume, donc
  jamais sur une base déjà en place.

## État

Fait : chaîne capteurs → MQTT → base → API → dashboard, authentification,
émission MQTT des commandes, déploiement automatisé sur la Pi.

Reste : le service qui écoute `botanik/commandes/#` et actionne le
matériel, le retour d'état sur `botanik/etat/<actionneur>`, le matériel
lui-même (rien n'est acheté, tout tourne en mode simulé), et le réseau de
neurones.
