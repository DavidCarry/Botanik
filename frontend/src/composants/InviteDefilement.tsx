import { useEffect, useState } from 'react'
import { LuChevronDown } from 'react-icons/lu'

/** Invite a faire defiler, sous les mesures.
 *
 *  Elle s'efface des le premier defilement : une fois le geste compris,
 *  l'indication devient du bruit. Reservee au mobile : des la tablette,
 *  on passe d'une vue a l'autre lateralement. */
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
        'pointer-events-none flex flex-col items-center gap-1 pb-1 transition-opacity duration-500 md:hidden',
        visible ? 'opacity-100' : 'opacity-0',
      ].join(' ')}
    >
      <span className="text-nano uppercase tracking-etiquette text-texte-faible">
        Faire défiler
      </span>
      <LuChevronDown size={18} className="invite-chevron text-texte-faible" />
    </div>
  )
}
