import {
  LuGauge, LuLayoutDashboard, LuScanFace, LuSlidersHorizontal,
} from 'react-icons/lu'
import type { IconType } from 'react-icons'

/** Les vues de l'application.
 *
 *  En dessous du grand format elles s'empilent et defilent : la
 *  navigation n'a alors plus d'objet et disparait.
 *
 *  Dans son propre fichier, et non dans le Bandeau : une constante
 *  exportee depuis un module de composant casse le rechargement a chaud.
 */
export type Vue = 'mesures' | 'tableau' | 'regles' | 'visages'

type Description = {
  valeur: Vue
  libelle: string
  icone: IconType
  /** Reservee aux comptes ouverts : regler la serre est un acte, pas une
   *  consultation. */
  connecte?: boolean
}

const TOUTES: Description[] = [
  { valeur: 'mesures', libelle: 'Mesures', icone: LuGauge },
  { valeur: 'tableau', libelle: 'Tableau de bord', icone: LuLayoutDashboard },
  { valeur: 'regles', libelle: 'Réglages', icone: LuSlidersHorizontal,
    connecte: true },
  // Sa propre page, et non une colonne des réglages : les deux listes
  // sont longues, et les mettre côte à côte enfermait chacune dans un
  // demi-écran qui défilait pour son compte.
  { valeur: 'visages', libelle: 'Visages', icone: LuScanFace,
    connecte: true },
]

/** Les vues accessibles en ce moment.
 *
 *  La navigation, les fleches et le glissement s'appuient tous dessus :
 *  une seule liste, sinon un rang calcule sur trois vues ferait glisser
 *  vers une page qui n'existe pas.
 */
export function vues(connecte: boolean): Description[] {
  return TOUTES.filter((v) => !v.connecte || connecte)
}
