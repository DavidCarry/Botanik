import { lireEvenements, type Evenement } from './api'
import { useSondage } from './useSondage'

// Le journal se lit comme il se vit : une commande ou une alerte doit
// apparaitre dans la seconde. C'est le seul panneau qui raconte ce qui
// s'est passe, et un decalage de cinq secondes suffisait a ce qu'on ne
// fasse plus le lien entre un interrupteur bascule et sa ligne.
const RAFRAICHISSEMENT_MS = 1000

/** Les dernieres commandes emises, toutes origines confondues.
 *
 *  Le journal est tenu par le collecteur, qui ecoute le topic : une
 *  commande du modele y figure donc au meme titre qu'un clic.
 *
 *  Null tant que rien n'est arrive, pour distinguer « on lit encore » de
 *  « il n'y a rien a lire ». Serveur injoignable : une liste vide, car
 *  attendre indefiniment un journal qui ne viendra pas n'apprend rien. */
export function useEvenements() {
  const { valeur, joignable } = useSondage<Evenement[] | null>(
    lireEvenements, RAFRAICHISSEMENT_MS, null,
  )
  return joignable ? valeur : valeur ?? []
}
