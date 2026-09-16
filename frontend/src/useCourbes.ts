import { useCallback, useEffect, useState } from 'react'
import {
  lireCapteurs, lireHistorique, type Capteur, type Fenetre, type Point,
} from './api'
import { useSondage } from './useSondage'

// Le dernier intervalle agrege se remplit au fil des mesures : en le
// relisant souvent, la courbe avance sous les yeux.
const RAFRAICHISSEMENT_MS = 10_000

/** Etat partage entre l'en-tete du panneau et le trace : le titre, la
 *  valeur courante et les selecteurs vivent dans la barre de titre, le
 *  graphique dans le corps. Un hook evite de faire remonter l'etat
 *  jusqu'a App, et garde ce fichier hors des modules de composants
 *  (le rechargement a chaud n'aime pas les melanger). */
export function useCourbes() {
  const [capteurs, setCapteurs] = useState<Capteur[]>([])
  const [choisi, setChoisi] = useState('')
  const [fenetre, setFenetre] = useState<Fenetre>('1j')

  // La liste vient du registre backend : aucune valeur en dur ici.
  useEffect(() => {
    let vivant = true
    lireCapteurs()
      .then((d) => {
        if (!vivant) return
        setCapteurs(d)
        setChoisi((c) => c || d[0]?.id || '')
      })
      .catch(() => undefined)
    return () => { vivant = false }
  }, [])

  // Changer de capteur ou de periode, c'est poser une autre question :
  // le sondage vide alors le trace au lieu de laisser l'ancien sous un
  // titre qui ne lui correspond plus.
  const lire = useCallback(
    () => (choisi ? lireHistorique(choisi, fenetre) : Promise.resolve([])),
    [choisi, fenetre],
  )
  const { valeur: points } = useSondage<Point[]>(
    choisi ? lire : null, RAFRAICHISSEMENT_MS, [],
  )

  return {
    capteurs, choisi, setChoisi, fenetre, setFenetre, points,
    capteur: capteurs.find((c) => c.id === choisi),
  }
}

export type EtatCourbes = ReturnType<typeof useCourbes>
