import { useEffect } from 'react'

/** Un evenement pousse par le serveur : une mesure, ou l'etat d'un
 *  actionneur. Le `genre` les distingue -- sans lui, « lumiere » serait
 *  ambigu, puisque c'est a la fois un actionneur et une grandeur. */
export type Pousse =
  | {
      genre: 'mesure'; capteur: string; valeur: number; unite: string; ts: string
      /** true : la sonde n'a pas répondu, la valeur vient du simulateur. */
      simule?: boolean
    }
  | {
      genre: 'etat'; actionneur: string; valeur: number; ts: string
      contenu?: unknown; lignes?: string[]
      /** true : rien ne repond, l'ordre est accepte sans effet. */
      simule?: boolean
    }

/** S'abonne au flux du serveur.
 *
 *  UNE seule connexion, partagee par tous ceux qui ecoutent : chaque
 *  appel de ce hook s'inscrit sur la meme source. Ouvrir un EventSource
 *  par composant multiplierait les connexions ouvertes pour rien, et le
 *  serveur les tient toutes.
 */
let source: EventSource | null = null
const ecouteurs = new Set<(p: Pousse) => void>()

function brancher() {
  if (source) return
  source = new EventSource('/api/flux')
  source.onmessage = (e) => {
    let p: Pousse
    try {
      p = JSON.parse(e.data)
    } catch {
      return
    }
    for (const ecouteur of ecouteurs) ecouteur(p)
  }
}

export function useFlux(surPoussee: (p: Pousse) => void) {
  useEffect(() => {
    ecouteurs.add(surPoussee)
    brancher()
    return () => {
      ecouteurs.delete(surPoussee)
      // Le dernier a partir ferme la porte : garder une connexion
      // ouverte sans personne au bout occuperait une file cote serveur.
      if (ecouteurs.size === 0) {
        source?.close()
        source = null
      }
    }
  }, [surPoussee])
}
