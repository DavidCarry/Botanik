import { lireEvenements, type Evenement } from './api'
import { useSondage } from './useSondage'

const RAFRAICHISSEMENT_MS = 5000

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
