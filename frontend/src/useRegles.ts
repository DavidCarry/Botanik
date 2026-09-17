import { useCallback, useEffect, useRef, useState } from 'react'
import {
  lireReglages, poserRegle, retirerRegle,
  type BorneRegle, type Reglages,
} from './api'

// Les seuils appris se deplacent avec la chaleur et la lumiere : les
// relire regulierement evite d'afficher un « suit l'IA : 50,6 % » perime.
const RAFRAICHISSEMENT_MS = 15_000

const VIDE: Reglages = { grandeurs: [], actionneurs: [] }

/** Les reglages, et de quoi les modifier.
 *
 *  Ce hook n'utilise pas `useSondage` : celui-ci vide sa valeur quand la
 *  question change, ce qui ferait clignoter la page a chaque
 *  enregistrement. Ici on veut l'inverse -- garder l'affichage et le
 *  remplacer en place.
 *
 *  Chaque enregistrement relance une lecture, car le serveur valide,
 *  borne et complete ce qu'on lui envoie : c'est SA version qui doit
 *  s'afficher ensuite, pas celle qu'on a saisie.
 */
export function useRegles() {
  const [reglages, setReglages] = useState<Reglages>(VIDE)
  const [joignable, setJoignable] = useState(true)
  const [occupe, setOccupe] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)

  const vivant = useRef(true)

  const relire = useCallback(() =>
    lireReglages()
      .then((d) => { if (vivant.current) { setReglages(d); setJoignable(true) } })
      .catch(() => { if (vivant.current) setJoignable(false) }),
  [])

  useEffect(() => {
    vivant.current = true
    const t = setInterval(relire, RAFRAICHISSEMENT_MS)
    relire()
    return () => { vivant.current = false; clearInterval(t) }
  }, [relire])

  const agir = useCallback(async (grandeur: string, faire: () => Promise<unknown>) => {
    setOccupe(grandeur)
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
    (grandeur: string, bas: BorneRegle, haut: BorneRegle) =>
      agir(grandeur, () => poserRegle(grandeur, bas, haut)),
    [agir],
  )

  const retirer = useCallback(
    (grandeur: string) => agir(grandeur, () => retirerRegle(grandeur)),
    [agir],
  )

  return { reglages, joignable, occupe, erreur, enregistrer, retirer }
}
