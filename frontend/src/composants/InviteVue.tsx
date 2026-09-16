import { LuChevronRight } from 'react-icons/lu'

/** Invite a passer a la vue suivante, au bord droit de l'ecran.
 *
 *  Elle s'efface en douceur sur la derniere vue plutot que de
 *  disparaitre : rien ne bouge autour d'elle. Reservee au grand format --
 *  en colonne, le defilement se comprend tout seul, et c'est
 *  InviteDefilement qui s'en charge.
 */
export default function InviteVue({
  visible, onSuivant,
}: { visible: boolean; onSuivant: () => void }) {
  return (
    <button
      type="button"
      onClick={onSuivant}
      aria-label="Vue suivante"
      aria-hidden={!visible}
      tabIndex={visible ? 0 : -1}
      className={[
        'fixed right-3 top-1/2 z-20 hidden size-11 -translate-y-1/2 place-items-center',
        'rounded-pilule text-texte-faible transition-opacity duration-500 lg:grid',
        'hover:text-texte',
        visible ? 'opacity-100' : 'pointer-events-none opacity-0',
      ].join(' ')}
    >
      <LuChevronRight size={24} className="invite-laterale" />
    </button>
  )
}
