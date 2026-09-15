type Option<T> = { valeur: T; libelle: string }

type Props<T extends string> = {
  options: Option<T>[]
  choisi: T
  onChange: (v: T) => void
  etiquette: string
}

/** Selecteur a choix unique, en pilules. Sert au capteur comme a la
 *  fenetre de temps : un seul composant, deux usages. */
export default function Pilules<T extends string>({
  options, choisi, onChange, etiquette,
}: Props<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={etiquette}
      className="flex shrink-0 gap-0.5 rounded-pilule border border-bordure bg-surface-creuse p-0.5"
    >
      {options.map((o) => {
        const actif = o.valeur === choisi
        return (
          <button
            key={o.valeur}
            type="button"
            role="radio"
            aria-checked={actif}
            onClick={() => onChange(o.valeur)}
            className={[
              'rounded-pilule px-2.5 py-1 text-micro font-medium',
              'transition-colors duration-200 whitespace-nowrap',
              actif
                ? 'bg-accent-voile text-accent-vif'
                : 'text-texte-faible hover:text-texte-doux',
            ].join(' ')}
          >
            {o.libelle}
          </button>
        )
      })}
    </div>
  )
}
