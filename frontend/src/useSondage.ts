import { useEffect, useRef, useState } from 'react'

/** Interroge le serveur a intervalle regulier, et survit a ses silences.
 *
 *  Cinq hooks repetaient la meme quinzaine de lignes : lire une fois,
 *  reposer la question toutes les N secondes, ignorer une reponse qui
 *  arrive apres que le composant a disparu. Le detail qui s'oubliait
 *  d'une copie a l'autre est justement le dernier -- un `setState` sur un
 *  composant demonte, et la console se remplit.
 *
 *  Une lecture ratee NE VIDE PAS ce qui est affiche : des valeurs justes
 *  d'il y a cinq secondes valent mieux qu'un ecran blanc. C'est
 *  `joignable` qui dit que la derniere tentative a echoue, a charge de
 *  l'appelant d'en faire ce qu'il veut.
 *
 *  Changer de question, en revanche, efface la reponse : afficher
 *  l'historique de la temperature sous le titre « luminosite » serait
 *  pire qu'un cadre vide. `lire` doit donc etre stable -- un
 *  `useCallback` -- et ne changer que lorsqu'on demande autre chose.
 *
 *  `lire` a null suspend le sondage, tant qu'on ne sait pas quoi demander.
 */
export function useSondage<T>(
  lire: (() => Promise<T>) | null,
  periode: number,
  initial: T,
): { valeur: T; joignable: boolean } {
  const [valeur, setValeur] = useState<T>(initial)
  const [joignable, setJoignable] = useState(true)

  // Capturee au premier rendu : l'appelant la recree souvent -- un
  // litteral `[]` -- mais elle designe toujours la meme chose, et elle
  // n'a donc pas a relancer le sondage.
  const vide = useRef(initial)
  const premier = useRef(true)

  useEffect(() => {
    if (!lire) return
    if (!premier.current) setValeur(vide.current)
    premier.current = false

    let vivant = true
    const relire = () =>
      lire()
        .then((v) => { if (vivant) { setValeur(v); setJoignable(true) } })
        .catch(() => { if (vivant) setJoignable(false) })

    relire()
    const t = setInterval(relire, periode)
    return () => { vivant = false; clearInterval(t) }
  }, [lire, periode])

  return { valeur, joignable }
}
