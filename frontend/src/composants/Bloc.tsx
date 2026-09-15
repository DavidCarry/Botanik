import type { ReactNode } from 'react'

type Props = {
  /** Commandes du bloc, posees sur une ligne au-dessus du contenu. */
  actions?: ReactNode
  children?: ReactNode
}

/** Bloc de contenu.
 *
 *  Sans cadre ni fond : dans cette colonne, tout repose directement sur
 *  le fond de page, et un panneau de verre y ferait une piece rapportee.
 *  Le bloc n'apporte que la mise en colonne -- un en-tete qui garde sa
 *  hauteur, un corps qui prend le reste sans jamais deborder.
 */
export default function Bloc({ actions, children }: Props) {
  return (
    <section className="relative flex min-h-0 flex-col overflow-hidden">
      {actions && (
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-1.5 pb-2 pt-1">
          {actions}
        </div>
      )}
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  )
}
