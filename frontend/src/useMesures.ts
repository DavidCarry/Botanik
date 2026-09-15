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

/** Retard d'un capteur sur le plus recent au-dela duquel on le declare
 *  muet. Volontairement large -- douze cycles a la cadence par defaut :
 *  une bulle qui clignote a la moindre hesitation ne servirait a rien,
 *  alors qu'une sonde debranchee ne revient pas toute seule. */
const SILENCE_MS = 60_000

/** Les capteurs dont la derniere mesure est tres en retard sur les
 *  autres.
 *
 *  La comparaison se fait entre capteurs, jamais avec l'horloge du
 *  navigateur : celle d'un telephone mal regle donnerait de fausses
 *  alertes. Et si TOUS se taisent, aucun n'est en retard sur les
 *  autres -- c'est alors la chaine entiere qui est en cause, ce que
 *  signale l'indicateur de liaison, pas les bulles. */
function muets(capteurs: Capteur[]): Set<string> {
  const instants = capteurs
    .map((c) => (c.mesure ? Date.parse(c.mesure.ts) : NaN))
    .filter((t) => !Number.isNaN(t))
  if (instants.length === 0) return new Set()

  const recent = Math.max(...instants)
  return new Set(
    capteurs
      .filter((c) => c.mesure && recent - Date.parse(c.mesure.ts) > SILENCE_MS)
      .map((c) => c.id),
  )
}

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

  return { capteurs, muets: muets(capteurs ?? []) }
}
