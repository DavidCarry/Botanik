#!/usr/bin/env bash
# Installe les quatre services Botanik dans systemd : ils redemarrent seuls
# apres un plantage et au demarrage de la machine.
set -euo pipefail

ICI="$(cd "$(dirname "$0")" && pwd)"
RACINE="$(cd "$ICI/../.." && pwd)"
UTILISATEUR="$(id -un)"

echo "installation depuis $RACINE (utilisateur $UTILISATEUR)"

for S in collecteur publisher actionneurs api; do
  sed -e "s|__RACINE__|$RACINE|g" -e "s|__USER__|$UTILISATEUR|g" \
      "$ICI/botanik-$S.service" \
    | sudo tee "/etc/systemd/system/botanik-$S.service" > /dev/null
done

# Autorise le redeploiement sans mot de passe, uniquement pour ces trois
# services : deployer.sh doit pouvoir les relancer sans intervention.
sudo tee /etc/sudoers.d/botanik > /dev/null <<SUDO
$UTILISATEUR ALL=(root) NOPASSWD: /usr/bin/systemctl restart botanik-collecteur.service, /usr/bin/systemctl restart botanik-publisher.service, /usr/bin/systemctl restart botanik-actionneurs.service, /usr/bin/systemctl restart botanik-api.service
SUDO
sudo chmod 440 /etc/sudoers.d/botanik

sudo systemctl daemon-reload
sudo systemctl enable --now botanik-collecteur botanik-publisher botanik-actionneurs botanik-api

echo
systemctl --no-pager --lines=0 status botanik-collecteur botanik-publisher botanik-actionneurs botanik-api \
  | grep -E 'botanik-|Active:'
