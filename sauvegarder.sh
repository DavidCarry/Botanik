#!/usr/bin/env bash
# Sauvegarde la base dans sauvegardes/, et ne garde que les 14 dernieres.
#
# Le sujet demande que l'installation tourne plusieurs semaines. Or tout
# l'historique de germination -- la demonstration ET le jeu de donnees du
# modele -- vit dans un unique volume Docker, sur une carte SD. Un
# `docker compose down -v` malheureux ou une carte fatiguee suffisent a
# tout perdre.
#
# pg_dump est appele DANS le conteneur : rien a installer sur l'hote.
set -euo pipefail

RACINE="$(cd "$(dirname "$0")" && pwd)"
DOSSIER="$RACINE/sauvegardes"
mkdir -p "$DOSSIER"

FICHIER="$DOSSIER/botanik-$(date +%Y%m%d-%H%M).sql.gz"
docker exec botanik-db pg_dump -U botanik -d botanik | gzip > "$FICHIER"

# Une archive vide vaut pire que pas d'archive : elle donne l'illusion
# d'etre couvert. On la refuse plutot que de la garder.
TAILLE=$(wc -c < "$FICHIER")
if [ "$TAILLE" -lt 1000 ]; then
  rm -f "$FICHIER"
  echo "sauvegarde vide ou incomplete -- rien n'a ete garde" >&2
  exit 1
fi

# Rotation : les 14 plus recentes, le reste part.
ls -1t "$DOSSIER"/botanik-*.sql.gz 2>/dev/null | tail -n +15 | while read -r VIEUX; do
  rm -f "$VIEUX"
done

echo "$(basename "$FICHIER")  $(numfmt --to=iec "$TAILLE" 2>/dev/null || echo "$TAILLE o")"
