import type { CapacitorConfig } from '@capacitor/cli'

/** L'application Android embarque l'interface et va chercher les données
 *  sur la serre.
 *
 *  Il n'y a pas de `server.url` : les pages viennent de l'APK, pas du
 *  serveur. L'adresse de la Pi, elle, est posée à la compilation par la
 *  variable `VITE_API` — voir le script `build:app`.
 *
 *  `androidScheme` vaut « http » et non « https », et c'est délibéré :
 *  une page servie en https ne peut pas appeler une API en clair, le
 *  navigateur bloque le contenu mixte. La serre n'a pas de certificat, et
 *  n'en a pas besoin sur un réseau local isolé.
 */
const config: CapacitorConfig = {
  appId: 'fr.botanik.serre',
  appName: 'Botanik',
  webDir: 'dist',

  android: {
    // Le fond de l'interface est sombre : un démarrage sur fond blanc
    // ferait un éclair désagréable avant le premier rendu.
    backgroundColor: '#0A1410',
  },

  server: {
    androidScheme: 'http',
  },
}

export default config
