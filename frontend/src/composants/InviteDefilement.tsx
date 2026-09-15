import { useEffect, useState } from 'react'
import { LuChevronDown } from 'react-icons/lu'

/** Invite a faire defiler, sous les mesures.
 *
 *  Elle s'efface des le premier defilement : une fois le geste compris,
 *  l'indication devient du bruit. Reservee aux formats en colonne --
 *  sur grand ecran tout tient deja dans la page. */
export default function InviteDefilement() {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const surDefilement = () => setVisible(window.scrollY < 40)
    window.addEventListener('scroll', surDefilement, { passive: true })
    return () => window.removeEventListener('scroll', surDefilement)
  }, [])

  return (
    <div
      aria-hidden
      className={[
        'pointer-events-none flex flex-col items-center gap-1 pb-1 transition-opacity duration-500 lg:hidden',
        visible ? 'opacity-100' : 'opacity-0',
      ].join(' ')}
    >
      <span className="text-[0.6rem] uppercase tracking-[0.16em] text-texte-faible">
        Faire défiler
      </span>
      <LuChevronDown size={18} className="invite-chevron text-texte-faible" />
    </div>
  )
}
