#!/usr/bin/env bash
# Installe les services Botanik dans systemd : ils redemarrent seuls apres
# un plantage et au demarrage de la machine. Installe aussi la sauvegarde
# quotidienne de la base.
set -euo pipefail

ICI="$(cd "$(dirname "$0")" && pwd)"
RACINE="$(cd "$ICI/../.." && pwd)"
UTILISATEUR="$(id -un)"

# La liste, ecrite UNE fois : elle servait a cinq endroits, et un service
# ajoute n'etait installe qu'a moitie si l'on en oubliait un.
SERVICES="collecteur publisher actionneurs cerveau camera visages api"
UNITES=""
for S in $SERVICES; do UNITES="$UNITES botanik-$S"; done

echo "installation depuis $RACINE (utilisateur $UTILISATEUR)"

# Le broker refuse les anonymes : sans ce fichier de mots de passe, aucun
# service ne peut se connecter.
"$RACINE/infra/initialiser-secrets.sh"

for S in $SERVICES; do
  sed -e "s|__RACINE__|$RACINE|g" -e "s|__USER__|$UTILISATEUR|g" \
      "$ICI/botanik-$S.service" \
    | sudo tee "/etc/systemd/system/botanik-$S.service" > /dev/null
done

# Autorise le redeploiement sans mot de passe, uniquement pour ces
# services : deployer.sh doit pouvoir les relancer sans intervention.
PERMIS=""
for U in $UNITES; do
  PERMIS="${PERMIS:+$PERMIS, }/usr/bin/systemctl restart $U.service"
done
sudo tee /etc/sudoers.d/botanik > /dev/null <<SUDO
$UTILISATEUR ALL=(root) NOPASSWD: $PERMIS
SUDO
sudo chmod 440 /etc/sudoers.d/botanik

# La sauvegarde n'est pas un service qui tourne mais une tache
# periodique : une unite oneshot, declenchee par un minuteur.
for F in botanik-sauvegarde.service botanik-sauvegarde.timer; do
  sed -e "s|__RACINE__|$RACINE|g" -e "s|__USER__|$UTILISATEUR|g" "$ICI/$F" \
    | sudo tee "/etc/systemd/system/$F" > /dev/null
done

sudo systemctl daemon-reload
sudo systemctl enable --now botanik-sauvegarde.timer
# shellcheck disable=SC2086
sudo systemctl enable --now $UNITES

echo
# shellcheck disable=SC2086
systemctl --no-pager --lines=0 status $UNITES | grep -E 'botanik-|Active:'
