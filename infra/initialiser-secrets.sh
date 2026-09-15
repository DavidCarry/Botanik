#!/usr/bin/env bash
# Cree les secrets locaux s'ils n'existent pas encore.
#
# Un seul mot de passe MQTT, tire au hasard, partage entre le broker et
# les quatre services. Il vit dans .env, hors du depot : cloner le projet
# ne donne acces a rien, et chaque installation a le sien.
#
# Idempotent : relancer ce script ne regenere rien. Pour repartir de zero,
# supprimer .env et infra/mosquitto/passwd, puis relancer.
set -euo pipefail

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
ENV="$RACINE/.env"
PASSWD="$RACINE/infra/mosquitto/passwd"

if [ ! -f "$ENV" ]; then
  MDP="$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | cut -c1-24)"
  cat > "$ENV" <<FIN
# Secrets locaux de Botanik -- hors depot, voir .gitignore.
# Lu automatiquement par backend/config.py.
MQTT_UTILISATEUR=botanik
MQTT_MDP=$MDP
FIN
  chmod 600 "$ENV" 2>/dev/null || true
  echo "  .env cree"
else
  echo "  .env deja present"
fi

set -a; . "$ENV"; set +a

if [ ! -f "$PASSWD" ]; then
  # Le hachage est fait par mosquitto lui-meme : pas besoin de l'outil sur
  # la machine hote, l'image du broker le porte deja.
  #
  # Le fichier doit ensuite appartenir au compte mosquitto (uid 1883) : le
  # broker ne tourne pas en root, et mosquitto_passwd cree un fichier
  # lisible du seul proprietaire. Sans ce chown, le broker refuse de
  # demarrer -- "Unable to open pwfile".
  MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$RACINE/infra/mosquitto:/config" eclipse-mosquitto:2 \
    sh -c "mosquitto_passwd -b -c /config/passwd '$MQTT_UTILISATEUR' '$MQTT_MDP' &&
           chown mosquitto:mosquitto /config/passwd &&
           chmod 600 /config/passwd"
  echo "  fichier de mots de passe du broker cree"
else
  echo "  passwd du broker deja present"
fi
