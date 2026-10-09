type Props = {
  rang: number
  total: number
  onAller: (rang: number) => void
}

/** Où l'on en est dans les pages du mobile, et de quoi y sauter.
 *
 *  Une colonne de pastilles au bord gauche : avec six pages et aucun
 *  défilement libre, rien d'autre ne dirait où l'on se trouve. La page
 *  courante s'allonge plutôt que de changer de couleur seulement — ça
 *  se repère du coin de l'œil.
 *
 *  Le geste, lui, n'a pas besoin d'aide : c'est `InviteDefilement`, sur
 *  la première page, qui l'annonce une fois pour toutes.
 *
 *  Absente au-delà de `md` : les vues y glissent latéralement, et c'est
 *  `FlechesVue` qui s'en charge.
 */
export default function NavPages({ rang, total, onAller }: Props) {
  // Une seule page : il n'y a nulle part où aller.
  if (total < 2) return null

  return (
    <nav
      aria-label="Pages"
      className="fixed left-2 top-1/2 z-20 flex -translate-y-1/2 flex-col
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
  )
}
