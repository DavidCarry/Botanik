import { useEffect, useState } from 'react'
import { lireSante, type Sante } from './api'

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
  const [sante, setSante] = useState<Sante | null>(null)
  const [joignable, setJoignable] = useState(true)

  useEffect(() => {
    let vivant = true
    const relire = () =>
      lireSante()
        .then((s) => { if (vivant) { setSante(s); setJoignable(true) } })
        .catch(() => { if (vivant) setJoignable(false) })

    relire()
    const t = setInterval(relire, RAFRAICHISSEMENT_MS)
    return () => { vivant = false; clearInterval(t) }
  }, [])

  return { sante, joignable }
}
