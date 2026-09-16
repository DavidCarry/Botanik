import { LuChevronLeft, LuChevronRight } from 'react-icons/lu'
import type { IconType } from 'react-icons'

type Props = {
  rang: number
  total: number
  onAller: (rang: number) => void
}

const BASE =
  'fixed top-1/2 z-20 hidden size-11 -translate-y-1/2 place-items-center ' +
  'rounded-pilule transition-colors duration-300 lg:grid'

/** Les fleches de changement de vue, aux deux bords de la page.
 *
 *  Aux extremites elles s'eteignent plutot que de disparaitre : rien ne
 *  bouge autour d'elles, et l'oeil sait toujours ou les retrouver.
 *
 *  Seule celle de droite bat. L'animation est une invitation a decouvrir
 *  la suite ; revenir en arriere n'a pas besoin d'etre suggere, le geste
 *  est deja connu une fois qu'on est alle voir.
 *
 *  Reservee au grand format : en colonne, on defile, et c'est
 *  InviteDefilement qui s'en charge.
 */
export default function FlechesVue({ rang, total, onAller }: Props) {
  const fleche = (
    delta: number, Icone: IconType, cote: string, etiquette: string, bat: boolean,
  ) => {
    const cible = rang + delta
    const actif = cible >= 0 && cible < total
    return (
      <button
        type="button"
        onClick={() => actif && onAller(cible)}
        disabled={!actif}
        aria-label={etiquette}
        className={[
          BASE, cote,
          actif
            ? 'text-texte-faible hover:bg-surface-haute hover:text-texte'
            : 'cursor-not-allowed text-texte-faible/20',
        ].join(' ')}
      >
        <Icone size={24} className={actif && bat ? 'invite-laterale' : undefined} />
      </button>
    )
  }

  return (
    <>
      {fleche(-1, LuChevronLeft, 'left-3', 'Vue précédente', false)}
      {fleche(1, LuChevronRight, 'right-3', 'Vue suivante', true)}
    </>
  )
}
