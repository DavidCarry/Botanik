import { useCallback, useEffect, useRef, useState } from 'react'
import {
  lireReglagesVisages, poserRegleVisage, retirerRegleVisage,
  type ActionRegle, type ReglagesVisages,
} from './api'
import { useFlux, type Pousse, type Visage } from './useFlux'

/** Les visages vus devant la serre, poussés par le serveur.
 *
 *  Aucune lecture initiale, et aucune n'est nécessaire : tant qu'il y a
 *  quelqu'un devant la caméra, la liste est republiée à chaque image.
 *  Un onglet ouvert au milieu d'un passage a donc son cadre en un
 *  dixième de seconde, sans rien avoir à demander.
 */
export function useVisages(): Visage[] {
  const [visages, setVisages] = useState<Visage[]>([])

  useFlux(useCallback((p: Pousse) => {
    if (p.genre === 'visages') setVisages(p.visages)
  }, []))

  return visages
}

// Les personnes n'apparaissent qu'en apprenant un visage, ce qui se fait
// hors de l'écran : une relecture de temps en temps suffit à voir
// arriver un nouveau venu.
const RAFRAICHISSEMENT_MS = 15_000

const VIDE: ReglagesVisages = {
  speciaux: [], personnes: [], regles: {}, actionneurs: [],
}

/** Qui la serre connaît, ce qu'elle en fait, et de quoi le modifier.
 *
 *  Même forme que `useRegles`, et pour la même raison : le serveur
 *  valide et complète ce qu'on lui envoie, donc c'est SA version qui
 *  doit s'afficher après un enregistrement, pas celle qu'on a saisie.
 */
export function useReglagesVisages() {
  const [reglages, setReglages] = useState<ReglagesVisages>(VIDE)
  const [occupe, setOccupe] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)

  const vivant = useRef(true)

  const relire = useCallback(() =>
    lireReglagesVisages()
      .then((d) => { if (vivant.current) setReglages(d) })
      .catch(() => { /* la page reste sur ce qu'elle montrait */ }),
  [])

  useEffect(() => {
    vivant.current = true
    const t = setInterval(relire, RAFRAICHISSEMENT_MS)
    relire()
    return () => { vivant.current = false; clearInterval(t) }
  }, [relire])

  const agir = useCallback(async (sujet: string, faire: () => Promise<unknown>) => {
    setOccupe(sujet)
    setErreur(null)
    try {
      await faire()
      await relire()
    } catch {
      setErreur('Enregistrement refusé')
    } finally {
      if (vivant.current) setOccupe(null)
    }
  }, [relire])

  const enregistrer = useCallback(
    (sujet: string, action: ActionRegle) =>
      agir(sujet, () => poserRegleVisage(sujet, action)),
    [agir],
  )

  const retirer = useCallback(
    (sujet: string) => agir(sujet, () => retirerRegleVisage(sujet)),
    [agir],
  )

  return { reglages, occupe, erreur, enregistrer, retirer }
}
