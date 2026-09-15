import { useEffect, useState } from 'react'
import { lireCapteurs, type Capteur } from './api'

/** Filet de securite, pas le mecanisme principal.
 *
 *  Si le flux se coupe et se rattache, quelques mesures ont pu passer a
 *  la tremie ; et un capteur active dans le registre n'apparaitrait
 *  jamais, le flux ne portant que des valeurs. Une relecture espacee
 *  remet tout d'aplomb sans rien couter. */
const RESYNCHRONISATION_MS = 60_000

type Poussee = { capteur: string; valeur: number; unite: string; ts: string }

/** Les mesures du moment, poussees par le serveur.
 *
 *  Deux sources, et c'est voulu : `/api/capteurs` donne l'etat initial --
 *  la derniere ligne en base, disponible des le premier affichage -- puis
 *  `/api/flux` pousse chaque nouvelle mesure a l'instant ou elle est
 *  publiee sur MQTT.
 *
 *  Interroger periodiquement, comme le font les courbes, ajoutait jusqu'a
 *  cinq secondes de retard pour une valeur qui n'a rien a calculer.
 *  `EventSource` se rattache tout seul si la liaison tombe.
 */
export function useMesures() {
  const [capteurs, setCapteurs] = useState<Capteur[] | null>(null)

  useEffect(() => {
    let vivant = true

    const relire = () =>
      lireCapteurs()
        .then((d) => { if (vivant) setCapteurs(d) })
        // On garde l'affichage en place : une lecture ratee ne vaut pas
        // d'effacer des valeurs justes.
        .catch(() => { if (vivant) setCapteurs((c) => c ?? []) })

    relire()
    const t = setInterval(relire, RESYNCHRONISATION_MS)

    const flux = new EventSource('/api/flux')
    flux.onmessage = (e) => {
      const p: Poussee = JSON.parse(e.data)
      setCapteurs((liste) =>
        liste?.map((c) =>
          c.id === p.capteur
            ? { ...c, mesure: { valeur: p.valeur, unite: p.unite, ts: p.ts } }
            : c,
        ) ?? liste,
      )
    }

    return () => { vivant = false; clearInterval(t); flux.close() }
  }, [])

  return capteurs
}
