import { useCallback, useState } from 'react'
import { useFlux, type Pousse, type Visage } from './useFlux'

/** Les visages vus devant la serre, pousses par le serveur.
 *
 *  Aucune lecture initiale, et aucune n'est necessaire : tant qu'il y a
 *  quelqu'un devant la camera, la liste est republiee a chaque image.
 *  Un onglet ouvert au milieu d'un passage a donc son cadre en un
 *  dixieme de seconde, sans rien avoir a demander.
 */
export function useVisages(): Visage[] {
  const [visages, setVisages] = useState<Visage[]>([])

  useFlux(useCallback((p: Pousse) => {
    if (p.genre === 'visages') setVisages(p.visages)
  }, []))

  return visages
}
