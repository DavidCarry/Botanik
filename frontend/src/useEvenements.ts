import { useEffect, useState } from 'react'
import { lireEvenements, type Evenement } from './api'

const RAFRAICHISSEMENT_MS = 5000

/** Les dernieres commandes emises, toutes origines confondues.
 *
 *  Le journal est tenu par le collecteur, qui ecoute le topic : une
 *  commande du modele y figure donc au meme titre qu'un clic. */
export function useEvenements() {
  const [liste, setListe] = useState<Evenement[] | null>(null)

  useEffect(() => {
    let vivant = true
    const relire = () =>
      lireEvenements()
        .then((e) => { if (vivant) setListe(e) })
        .catch(() => { if (vivant) setListe((l) => l ?? []) })
    relire()
    const t = setInterval(relire, RAFRAICHISSEMENT_MS)
    return () => { vivant = false; clearInterval(t) }
  }, [])

  return liste
}
