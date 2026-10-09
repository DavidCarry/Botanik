import { useCallback, useEffect, useRef, useState } from 'react'
import {
  lireReglages, poserLumiereUtile, poserRegle, retirerRegle,
  type BorneRegle, type ModeClarte, type Reglages,
} from './api'

// Les seuils appris se deplacent avec la chaleur et la lumiere : les
// relire regulierement evite d'afficher un « suit l'IA : 50,6 % » perime.
const RAFRAICHISSEMENT_MS = 15_000

// `lumiere_utile` n'a pas de defaut qui veuille dire quelque chose : il
// vit en base, avec un repli cote serveur. Ceci ne s'affiche jamais --
// la page annonce « Lecture des reglages... » tant que la liste est vide.
const VIDE: Reglages = {
  grandeurs: [], actionneurs: [],
  lumiere_utile: { mode: 'ia', valeur: null, appris: 0 },
}

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

  // Sa propre cle d'occupation, et non celle de la grandeur : le seuil
  // de clarte et les bornes de « Lumiere recue » s'enregistrent
  // separement, et l'un ne doit pas griser l'autre.
  const reglerLumiereUtile = useCallback(
    (mode: ModeClarte, utile: number | null) =>
      agir('lumiere_utile', () => poserLumiereUtile(mode, utile)),
    [agir],
  )

  const retirer = useCallback(
    (grandeur: string) => agir(grandeur, () => retirerRegle(grandeur)),
    [agir],
  )

  return { reglages, joignable, occupe, erreur, enregistrer, retirer,
           reglerLumiereUtile }
}
