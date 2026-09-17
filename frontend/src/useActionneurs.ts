import { useCallback, useEffect, useRef, useState } from 'react'
import { commander, lireActionneurs, type Actionneur, type Contenu } from './api'
import { useFlux, type Pousse } from './useFlux'

// Filet de securite : les etats arrivent par le flux, mais une attente
// qui n'aboutit pas doit finir par etre declaree -- et le verrou pose par
// une commande manuelle ne passe par aucun flux.
const RAFRAICHISSEMENT_MS = 5000

/** Au-dela, on cesse d'attendre la confirmation d'un actionneur. */
const PATIENCE_MS = 5000

type Attendu = { valeur: number; depuis: number }

/** Pilotage des actionneurs.
 *
 *  L'interrupteur n'affiche pas ce qu'il croit : il affiche ce que
 *  l'actionneur a annonce sur `botanik/etat/<id>`, pousse par le serveur
 *  a l'instant ou il l'annonce. Un clic n'est donc qu'une demande --
 *  tant que le materiel n'a pas repondu, la position affichee reste
 *  marquee comme une intention.
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

  // Les changements d'etat arrivent par le flux, sans attendre le
  // prochain battement : l'interrupteur bouge a l'instant ou le modele
  // agit, pas jusqu'a cinq secondes plus tard.
  const surPoussee = useCallback((p: Pousse) => {
    if (p.genre !== 'etat') return
    setListe((l) =>
      l.map((a) => (a.id === p.actionneur
        ? {
            ...a, valeur: p.valeur, ts: p.ts,
            // L'afficheur annonce aussi ce qu'il montre : sans cela, le
            // choix fait dans une fenetre ne se verrait pas dans l'autre.
            ...(p.contenu !== undefined ? { contenu: p.contenu as Contenu } : {}),
            ...(p.lignes !== undefined ? { lignes: p.lignes } : {}),
            ...(p.simule !== undefined ? { simule: p.simule } : {}),
          }
        : a)),
    )
    // L'attente prend fin des que l'actionneur confirme la valeur
    // demandee -- inutile d'attendre le prochain battement.
    setAttendus((a) => {
      const attendu = a[p.actionneur]
      if (!attendu || attendu.valeur !== p.valeur) return a
      const reste = { ...a }
      delete reste[p.actionneur]
      return reste
    })
  }, [])

  useFlux(surPoussee)

  useEffect(() => {
    let vivant = true

    const rafraichir = async () => {
      let recu: Actionneur[]
      try {
        recu = await lireActionneurs()
      } catch {
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

  const basculer = useCallback(async (id: string, valeur: number,
                                      contenu?: Contenu) => {
    setErreur(null)
    setAttendus((a) => ({ ...a, [id]: { valeur, depuis: Date.now() } }))
    try {
      await commander(id, valeur, contenu)
    } catch {
      setAttendus((a) => {
        const reste = { ...a }
        delete reste[id]
        return reste
      })
      setErreur('Commande refusée')
      return
    }
    // Relire tout de suite : le verrou vient de naitre, et lui seul ne
    // passe pas par le flux.
    await relire.current()
  }, [])

  return { liste, attendus, erreur, basculer }
}
