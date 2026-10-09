import { LuChevronDown } from 'react-icons/lu'

type Props = {
  rang: number
  total: number
  onAller: (rang: number) => void
}

/** La navigation entre les pages du mobile.
 *
 *  Une flèche en bas pour descendre d'une page, et une colonne de
 *  pastilles au bord droit pour savoir où on en est — avec six pages et
 *  aucun défilement libre, rien d'autre ne le dirait.
 *
 *  Absente au-delà de `md` : les vues y glissent latéralement, et c'est
 *  `FlechesVue` qui s'en charge.
 *
 *  La flèche BAT sur la première page seulement. L'animation est une
 *  invitation à découvrir la suite ; une fois le geste compris, elle
 *  deviendrait du bruit. C'est ce que faisait l'ancienne invite à
 *  défiler, qu'elle remplace.
 */
export default function NavPages({ rang, total, onAller }: Props) {
  // Une seule page : il n'y a nulle part où aller.
  if (total < 2) return null

  const dernier = rang >= total - 1

  return (
    <>
      <nav
        aria-label="Pages"
        className="fixed right-2 top-1/2 z-20 flex -translate-y-1/2 flex-col
                   items-center gap-2 md:hidden"
      >
        {Array.from({ length: total }, (_, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onAller(i)}
            aria-label={`Page ${i + 1} sur ${total}`}
            aria-current={i === rang ? 'true' : undefined}
            // La zone tactile fait 24 px, la pastille 6 : on vise large
            // sans alourdir le dessin.
            className="grid size-6 place-items-center"
          >
            <span
              className={`block rounded-pilule transition-all duration-300 ${
                i === rang
                  ? 'h-4 w-1.5 bg-accent-vif'
                  : 'size-1.5 bg-texte-faible/50'
              }`}
            />
          </button>
        ))}
      </nav>

      <button
        type="button"
        onClick={() => !dernier && onAller(rang + 1)}
        disabled={dernier}
        aria-label="Page suivante"
        className={`fixed bottom-3 left-1/2 z-20 grid size-10 -translate-x-1/2
                    place-items-center rounded-pilule bg-surface-creuse/80
                    backdrop-blur-sm transition-colors duration-300 md:hidden ${
          dernier
            ? 'cursor-not-allowed text-texte-faible/20'
            : 'text-texte-faible hover:text-texte'
        }`}
      >
        <LuChevronDown
          size={22}
          className={rang === 0 ? 'invite-chevron' : undefined}
        />
      </button>
    </>
  )
}
