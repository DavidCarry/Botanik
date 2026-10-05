# Adresse de la serre, posée dans l'application Android à la compilation.
#
# Ce fichier n'est lu que par `npm run build:app` (mode « app »). Le build
# web, lui, ne définit pas cette variable : il garde des chemins relatifs
# et reste servi par la Pi comme avant.
#
# Si l'adresse de la Raspberry Pi change, c'est ICI qu'on la corrige, puis
# on reconstruit l'APK.
VITE_API=http://192.168.50.74:8000
