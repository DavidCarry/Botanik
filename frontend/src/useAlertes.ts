import { lireAlertes, type Alerte } from './api'
import { useSondage } from './useSondage'

const RAFRAICHISSEMENT_MS = 5000

/** Les problemes en cours.
 *
 *  Plus frequent que les seuils : une alerte est ce qu'on veut voir tout
 *  de suite, et la liste est courte. */
export function useAlertes() {
  return useSondage<Alerte[]>(lireAlertes, RAFRAICHISSEMENT_MS, []).valeur
}
