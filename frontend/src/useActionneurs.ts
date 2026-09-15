import { useCallback, useEffect, useRef, useState } from 'react'
import { commander, lireActionneurs, type Actionneur } from './api'

const RAFRAICHISSEMENT_MS = 2000

/** Au-dela, on cesse d'attendre la confirmation d'un actionneur. */
const PATIENCE_MS = 5000

type Attendu = { valeur: number; depuis: number }

/** Pilotage des actionneurs.
 *
 *  L'interrupteur n'affiche plus ce qu'il croit : il affiche ce que
 *  l'actionneur a annonce sur `botanik/etat/<id>`. Un clic n'est donc
 *  qu'une demande -- tant que le materiel n'a pas repondu, la position
 *  affichee reste marquee comme une intention.
 *
 *  Sans ce detour, une pompe en panne donnerait exactement la meme image
 *  a l'ecran qu'une pompe qui tourne.
 */
export function useActionneurs() {
  const [liste, setListe] = useState<Actionneur[]>([])
  const [attendus, setAttendus] = useState<Record<string, Attendu>>({})
  const [erreur, setErreur] = useState<string | null>(null)

  /** Le battement vit dans l'effet ; `basculer` a besoin de le declencher
   *  hors du battement, d'ou ce relais. */
  const relire = useRef<() => Promise<void>>(async () => {})

  useEffect(() => {
    let vivant = true

    const rafraichir = async () => {
      let recu: Actionneur[]
      try {
        recu = await lireActionneurs()
      } catch {
        if (vivant) setListe([])
        return
      }
      if (!vivant) return
      setListe(recu)

      // Une attente prend fin quand l'actionneur confirme -- ou quand on
      // a trop patiente, auquel cas on le dit plutot que de laisser
      // l'interrupteur tourner indefiniment.
      setAttendus((en_cours) => {
        const restants: Record<string, Attendu> = {}
        let muet: string | null = null
        for (const [id, a] of Object.entries(en_cours)) {
          const actionneur = recu.find((x) => x.id === id)
          if (actionneur?.valeur === a.valeur) continue
          if (Date.now() - a.depuis > PATIENCE_MS) {
            muet = actionneur?.libelle ?? id
            continue
          }
          restants[id] = a
        }
        if (muet) setErreur(`${muet} n’a pas répondu`)
        return restants
      })
    }

    relire.current = rafraichir
    rafraichir()
    const t = setInterval(rafraichir, RAFRAICHISSEMENT_MS)
    return () => { vivant = false; clearInterval(t) }
  }, [])

  const basculer = useCallback(async (id: string, valeur: number) => {
    setErreur(null)
    setAttendus((a) => ({ ...a, [id]: { valeur, depuis: Date.now() } }))
    try {
      await commander(id, valeur)
    } catch {
      setAttendus((a) => {
        const reste = { ...a }
        delete reste[id]
        return reste
      })
      setErreur('Commande refusée')
      return
    }
    // Le service a pu repondre avant le prochain battement : on regarde
    // tout de suite plutot que d'attendre deux secondes pour rien.
    await relire.current()
  }, [])

  return { liste, attendus, erreur, basculer }
}
