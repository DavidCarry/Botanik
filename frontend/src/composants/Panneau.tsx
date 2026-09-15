import type { ReactNode } from 'react'

type Props = {
  /** Absent : aucune ligne d'en-tete n'est reservee. */
  titre?: string
  /** Pose sur la meme ligne que le titre, aligne a droite. */
  actions?: ReactNode
  /** Sans cadre de verre : le contenu repose directement sur le fond. */
  nu?: boolean
  children?: ReactNode
}

/** Conteneur de bloc.
 *
 *  Deux regimes d'en-tete :
 *  - sans `actions`, le titre est pose EN SUPERPOSITION et ne prend
 *    aucune hauteur : le contenu peut remonter jusqu'en haut ;
 *  - avec `actions`, il partage une vraie ligne avec elles.
 */
export default function Panneau({ titre, actions, nu, children }: Props) {
  const enTete = titre !== undefined || actions !== undefined
  const enLigne = actions !== undefined

  return (
    <section
      className={[
        'relative flex min-h-0 flex-col overflow-hidden',
        nu ? '' : 'panneau min-h-[210px] rounded-bloc p-2 sm:p-2.5 lg:min-h-0',
      ].join(' ')}
    >
      {enTete && (
        <div
          className={
            enLigne
              ? 'flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-1.5 pb-2 pt-1'
              : 'pointer-events-none absolute left-3.5 top-3 z-10 sm:left-4 sm:top-3.5'
          }
        >
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
