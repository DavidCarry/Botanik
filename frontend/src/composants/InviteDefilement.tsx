import { LuChevronDown } from 'react-icons/lu'

/** Invite à passer à la page suivante, sous les mesures.
 *
 *  Elle ne s'efface plus d'elle-même et n'a plus rien à écouter : elle
 *  vit DANS la première page, et disparaît donc avec elle dès qu'on
 *  passe à la suivante. Une fois le geste compris, l'indication ne
 *  revient que si l'on revient au début — ce qui est exactement ce
 *  qu'on veut d'une invite.
 *
 *  Décorative, et rien d'autre : le geste se fait au doigt, et les
 *  pastilles du bord droit servent à sauter d'une page à l'autre.
 *
 *  Réservée au mobile : dès la tablette, on passe d'une vue à l'autre
 *  latéralement.
 */
export default function InviteDefilement() {
  return (
    <div
      aria-hidden
      className="pointer-events-none flex shrink-0 flex-col items-center
                 gap-1 pt-2 md:hidden"
    >
      <span className="text-nano uppercase tracking-etiquette text-texte-faible">
        Faire défiler
      </span>
      <LuChevronDown size={18} className="invite-chevron text-texte-faible" />
    </div>
  )
}
