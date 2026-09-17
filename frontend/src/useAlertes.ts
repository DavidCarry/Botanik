import { lireAlertes, type Alerte } from './api'
import { useSondage } from './useSondage'

// Meme seconde que le journal : une alerte qui s'y affiche pendant que
// le voyant de la barre reste eteint donnerait deux versions des faits.
const RAFRAICHISSEMENT_MS = 1000

/** Les problemes en cours.
 *
 *  Plus frequent que les seuils : une alerte est ce qu'on veut voir tout
 *  de suite, et la liste est courte. */
export function useAlertes() {
  return useSondage<Alerte[]>(lireAlertes, RAFRAICHISSEMENT_MS, []).valeur
}
