import { useCallback, useState } from 'react'
import { useFlux, type Pousse, type Visage } from './useFlux'

/** Les visages vus devant la serre, pousses par le serveur.
 *
 *  Aucune lecture initiale : le message est RETENU par le broker, donc
 *  la premiere poussee arrive dans la foulee de la connexion. Interroger
 *  une route en plus ne ferait que redemander ce qui vient tout seul.
 */
export function useVisages(): Visage[] {
  const [visages, setVisages] = useState<Visage[]>([])

  useFlux(useCallback((p: Pousse) => {
    if (p.genre === 'visages') setVisages(p.visages)
  }, []))

  return visages
}
