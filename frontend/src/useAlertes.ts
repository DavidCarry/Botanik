import { useEffect, useState } from 'react'
import { lireAlertes, type Alerte } from './api'

const RAFRAICHISSEMENT_MS = 5000

/** Les problemes en cours.
 *
 *  Plus frequent que les seuils : une alerte est ce qu'on veut voir tout
 *  de suite, et la liste est courte. */
export function useAlertes() {
  const [liste, setListe] = useState<Alerte[]>([])

  useEffect(() => {
    let vivant = true
    const relire = () =>
      lireAlertes()
        .then((a) => { if (vivant) setListe(a) })
        .catch(() => undefined)
    relire()
    const t = setInterval(relire, RAFRAICHISSEMENT_MS)
    return () => { vivant = false; clearInterval(t) }
  }, [])

  return liste
}
