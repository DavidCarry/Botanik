#!/usr/bin/env bash
# Installe les services Botanik dans systemd : ils redemarrent seuls apres
# un plantage et au demarrage de la machine. Installe aussi la sauvegarde
# quotidienne de la base.
set -euo pipefail

ICI="$(cd "$(dirname "$0")" && pwd)"
RACINE="$(cd "$ICI/../.." && pwd)"
UTILISATEUR="$(id -un)"

echo "installation depuis $RACINE (utilisateur $UTILISATEUR)"

# Le broker refuse les anonymes : sans ce fichier de mots de passe, aucun
# service ne peut se connecter.
"$RACINE/infra/initialiser-secrets.sh"

for S in collecteur publisher actionneurs cerveau api; do
  sed -e "s|__RACINE__|$RACINE|g" -e "s|__USER__|$UTILISATEUR|g" \
      "$ICI/botanik-$S.service" \
    | sudo tee "/etc/systemd/system/botanik-$S.service" > /dev/null
done

# Autorise le redeploiement sans mot de passe, uniquement pour ces trois
# services : deployer.sh doit pouvoir les relancer sans intervention.
sudo tee /etc/sudoers.d/botanik > /dev/null <<SUDO
$UTILISATEUR ALL=(root) NOPASSWD: /usr/bin/systemctl restart botanik-collecteur.service, /usr/bin/systemctl restart botanik-publisher.service, /usr/bin/systemctl restart botanik-actionneurs.service, /usr/bin/systemctl restart botanik-cerveau.service, /usr/bin/systemctl restart botanik-api.service
SUDO
sudo chmod 440 /etc/sudoers.d/botanik

# La sauvegarde n'est pas un service qui tourne mais une tache
# periodique : une unite oneshot, declenchee par un minuteur.
for F in botanik-sauvegarde.service botanik-sauvegarde.timer; do
  sed -e "s|__RACINE__|$RACINE|g" -e "s|__USER__|$UTILISATEUR|g" "$ICI/$F"     | sudo tee "/etc/systemd/system/$F" > /dev/null
done

sudo systemctl daemon-reload
sudo systemctl enable --now botanik-sauvegarde.timer
sudo systemctl enable --now botanik-collecteur botanik-publisher botanik-actionneurs botanik-cerveau botanik-api

echo
systemctl --no-pager --lines=0 status botanik-collecteur botanik-publisher botanik-actionneurs botanik-cerveau botanik-api \
  | grep -E 'botanik-|Active:'
