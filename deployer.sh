#!/usr/bin/env bash
# Met a jour Botanik depuis GitHub et relance ce qui doit l'etre.
# Ne refait que le necessaire : modifier un fichier Python ne declenche
# pas un rebuild du frontend.
set -uo pipefail

RACINE="$(cd "$(dirname "$0")" && pwd)"
cd "$RACINE" || exit 1

echo "== mise a jour =="
AVANT="$(git rev-parse HEAD)"
if ! git pull --ff-only 2>&1 | sed 's/^/  /'; then
  echo "  echec du pull" >&2
  exit 1
fi
APRES="$(git rev-parse HEAD)"

if [ "$AVANT" = "$APRES" ]; then
  echo "  deja a jour"
  MODIFIES=""
else
  git log --oneline "$AVANT..$APRES" | sed 's/^/  /'
  MODIFIES="$(git diff --name-only "$AVANT" "$APRES")"
fi

if echo "$MODIFIES" | grep -q '^backend/requirements.txt$'; then
  echo "== dependances python =="
  backend/.venv/bin/pip install -q -r backend/requirements.txt && echo "  ok"
fi

if echo "$MODIFIES" | grep -q '^frontend/package-lock.json$'; then
  echo "== dependances npm =="
  (cd frontend && npm ci --silent) && echo "  ok"
fi

# Le front est reconstruit s'il a change, ou s'il n'a jamais ete compile.
if [ ! -d frontend/dist ] || echo "$MODIFIES" | grep -q '^frontend/'; then
  echo "== build du frontend =="
  (cd frontend && npm run build 2>&1 | tail -4 | sed 's/^/  /')
fi

echo "== secrets =="
./infra/initialiser-secrets.sh

echo "== conteneurs =="
# Idempotent : garantit qu'ils tournent, et les recree si docker-compose.yml
# a change. Sans ca, une modif d'infra passait silencieusement a la trappe.
docker compose up -d 2>&1 | grep -v '^$' | tail -3 | sed 's/^/  /'

# Une config montee en volume n'est relue qu'au redemarrage du conteneur :
# `up -d` ne suffit pas, le conteneur n'ayant pas change.
if echo "$MODIFIES" | grep -q '^infra/mosquitto/'; then
  echo "  config mosquitto modifiee -> redemarrage du broker"
  docker compose restart broker > /dev/null
fi

if echo "$MODIFIES" | grep -q '^infra/postgres/init\.sql$'; then
  echo "  ATTENTION : init.sql a change, mais il n'est joue qu'a la CREATION"
  echo "  du volume. Pour l'appliquer :  docker compose down -v && docker compose up -d"
  echo "  (cela supprime toutes les mesures deja enregistrees)"
fi

docker compose ps --format '  {{.Name}}  {{.Status}}'

echo "== redemarrage =="
UNITES="botanik-collecteur botanik-publisher botanik-actionneurs botanik-cerveau botanik-camera botanik-visages botanik-api"
if systemctl list-unit-files 'botanik-*.service' --no-legend 2>/dev/null | grep -q .; then
  for U in $UNITES; do sudo systemctl restart "$U.service"; done
  sleep 3
  for U in $UNITES; do printf '  %-22s %s\n' "$U" "$(systemctl is-active "$U")"; done
else
  echo "  systemd absent, repli sur demarrer.sh"
  ./demarrer.sh
fi
