import type { ReactNode } from 'react'
import Jauge from './Jauge'

export type Etat = 'bon' | 'attention' | 'critique'

type Props = {
  icone: ReactNode
  libelle: string
  valeur: string
  unite?: string
  etat: Etat
  etatTexte: string
  plage?: { valeur: number; min: number; max: number; idealMin: number; idealMax: number }
}

// L'etat est toujours accompagne de son libelle : la couleur seule ne doit
// jamais porter l'information (daltonisme, impression, mode contraste).
const PASTILLE: Record<Etat, string> = {
  bon: 'bg-bon',
  attention: 'bg-attention',
  critique: 'bg-critique',
}

export default function Tuile({
  icone, libelle, valeur, unite, etat, etatTexte, plage,
}: Props) {
  return (
    <article
      className="group flex flex-col gap-3 rounded-2xl border border-hairline
                 bg-surface p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]
                 transition-colors hover:border-ink/20 sm:gap-4 sm:p-5"
    >
      <header className="flex items-center gap-2 text-muted">
        <span className="shrink-0">{icone}</span>
        <h3 className="truncate text-[13px] font-medium sm:text-sm">{libelle}</h3>
      </header>

      <p className="flex items-baseline gap-1.5">
        <span className="text-[28px] font-semibold leading-none tracking-tight text-ink sm:text-4xl">
          {valeur}
        </span>
        {unite && (
          <span className="text-sm font-medium text-muted sm:text-base">{unite}</span>
        )}
      </p>

      <div className="mt-auto flex flex-col gap-2">
        {plage && <Jauge {...plage} />}
        <p className="flex items-center gap-1.5 text-[11px] text-ink-2 sm:text-xs">
          <span className={`size-1.5 shrink-0 rounded-full ${PASTILLE[etat]}`} />
          <span className="truncate">{etatTexte}</span>
        </p>
      </div>
    </article>
  )
}
