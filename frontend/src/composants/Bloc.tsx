import type { ReactNode } from 'react'

type Props = {
  /** Absent : aucune ligne d'en-tete n'est reservee. */
  titre?: string
  /** Commandes du bloc, sur la meme ligne que le titre, a droite. */
  actions?: ReactNode
  children?: ReactNode
}

/** Bloc de contenu.
 *
 *  Sans cadre ni fond : tout repose directement sur le fond de page, et
 *  un panneau de verre y ferait une piece rapportee. Le bloc n'apporte
 *  que la mise en colonne -- un en-tete qui garde sa hauteur, un corps
 *  qui prend le reste sans jamais deborder.
 */
export default function Bloc({ titre, actions, children }: Props) {
  return (
    <section className="relative flex min-h-0 flex-col overflow-hidden">
      {(titre || actions) && (
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-1.5 pb-2 pt-1">
          {titre && (
            <h2 className="shrink-0 text-micro font-medium uppercase tracking-[0.14em] text-texte-faible">
              {titre}
            </h2>
          )}
          {actions}
        </div>
      )}
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  )
}
