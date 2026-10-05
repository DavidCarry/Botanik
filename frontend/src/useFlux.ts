import { useEffect } from 'react'
import { BASE } from './api'

/** Un visage vu dans la derniere image de la camera.
 *
 *  Les quatre nombres sont RELATIFS a l'image, de 0 a 1 : le coin haut
 *  gauche du cadre, puis sa largeur et sa hauteur. En pixels, il aurait
 *  fallu connaitre ici la resolution de la camera -- et la vue s'affiche
 *  tantot en vignette, tantot en plein ecran.
 *
 *  `nom` vaut « Personne » tant qu'aucune reference n'a ete enregistree. */
export type Visage = {
  x: number
  y: number
  l: number
  h: number
  nom: string
  score: number
}

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
      genre: 'plages'
      plages: Record<string, { bas: number | null; haut: number | null } | null>
    }
  | {
      genre: 'etat'; actionneur: string; valeur: number; ts: string
      contenu?: unknown; lignes?: string[]
      /** true : rien ne repond, l'ordre est accepte sans effet. */
      simule?: boolean
    }
  | {
      /** La LISTE complete des visages vus, et non un visage a la fois :
       *  c'est elle qui a un sens, celui qui s'en va devant disparaitre. */
      genre: 'visages'; visages: Visage[]
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
  // Le flux n'est pas protege : un EventSource ne sait pas porter
  // d'en-tete, et c'est tres bien ainsi -- il n'y a rien a
  // authentifier pour regarder des mesures.
  source = new EventSource(BASE + '/api/flux')
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
