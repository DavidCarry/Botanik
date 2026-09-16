import { LuGauge, LuLayoutDashboard, LuSprout } from 'react-icons/lu'
import type { IconType } from 'react-icons'

/** Les deux vues de l'application.
 *
 *  En dessous du grand format elles s'empilent et defilent : la
 *  navigation n'a alors plus d'objet et disparait.
 *
 *  Dans son propre fichier, et non dans le Bandeau : une constante
 *  exportee depuis un module de composant casse le rechargement a chaud.
 */
export type Vue = 'mesures' | 'serre' | 'tableau'

export const VUES: { valeur: Vue; libelle: string; icone: IconType }[] = [
  { valeur: 'mesures', libelle: 'Mesures', icone: LuGauge },
  { valeur: 'serre', libelle: 'La serre', icone: LuSprout },
  { valeur: 'tableau', libelle: 'Tableau de bord', icone: LuLayoutDashboard },
]
