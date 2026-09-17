import { lireModele, type Modele } from './api'
import { useSondage } from './useSondage'

// Les seuils bougent avec la temperature et la lumiere, qui evoluent en
// minutes, pas en secondes : inutile de les redemander plus souvent.
const RAFRAICHISSEMENT_MS = 30_000

/** Le reseau entraine et les seuils qu'il applique en ce moment.
 *
 *  Null tant qu'on n'a pas de reponse ; `entraine: false` si aucun modele
 *  n'est en base -- l'ecran retombe alors sur les plages du registre. */
export function useModele() {
  return useSondage<Modele | null>(lireModele, RAFRAICHISSEMENT_MS, null).valeur
}
