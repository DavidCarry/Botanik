#!/usr/bin/env bash
# Demarre, arrete ou inspecte les services de Botanik.
#   ./demarrer.sh            lance tout
#   ./demarrer.sh arreter    coupe tout
#   ./demarrer.sh etat       affiche ce qui tourne
set -uo pipefail

RACINE="$(cd "$(dirname "$0")" && pwd)"
LOGS="$RACINE/logs"
SERVICES='collecteur.py|publisher.py|main.py'

arreter() {
  pkill -f "$SERVICES" 2>/dev/null || true
}

etat() {
  echo "--- conteneurs ---"
  (cd "$RACINE" && docker compose ps --format 'table {{.Name}}\t{{.Status}}')
  echo
  echo "--- services python ---"
  pgrep -a -f "$SERVICES" || echo "  aucun"
}

case "${1:-demarrer}" in
  arreter)
    arreter
    echo "services arretes"
    ;;
  etat)
    etat
    ;;
  demarrer)
    arreter
    sleep 1
    mkdir -p "$LOGS"
    cd "$RACINE/backend" || exit 1

    # Le collecteur d'abord : il doit ecouter avant que le publisher emette.
    setsid nohup .venv/bin/python collecteur.py > "$LOGS/collecteur.log" 2>&1 < /dev/null &
    sleep 2
    setsid nohup .venv/bin/python publisher.py > "$LOGS/publisher.log" 2>&1 < /dev/null &
    setsid nohup .venv/bin/python main.py > "$LOGS/api.log" 2>&1 < /dev/null &
    sleep 3

    echo "services demarres, journaux dans $LOGS"
    ;;
  *)
    echo "usage: $0 [demarrer|arreter|etat]" >&2
    exit 1
    ;;
esac
