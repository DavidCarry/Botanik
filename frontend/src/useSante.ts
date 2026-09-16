import { lireSante, type Sante } from './api'
import { useSondage } from './useSondage'

const RAFRAICHISSEMENT_MS = 10_000

/** Sante de la chaine d'archivage.
 *
 *  Distincte de « l'API repond » : depuis que les bulles recoivent les
 *  mesures par le flux, un collecteur arrete laisse l'ecran parfaitement
 *  vivant pendant que plus rien n'est enregistre. Cette lecture est le
 *  seul endroit qui regarde la base plutot que le flux.
 *
 *  Null tant qu'on n'a pas de reponse : ne pas savoir n'est pas la meme
 *  chose qu'aller mal, et l'ecran ne doit pas crier au loup au premier
 *  affichage.
 */
export function useSante() {
  const { valeur, joignable } = useSondage<Sante | null>(
    lireSante, RAFRAICHISSEMENT_MS, null,
  )
  return { sante: valeur, joignable }
}
