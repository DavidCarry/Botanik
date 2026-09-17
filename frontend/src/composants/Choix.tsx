import { useEffect, useRef, useState } from 'react'
import { LuCheck, LuChevronDown } from 'react-icons/lu'

type Option = { valeur: string; libelle: string }

/** Liste deroulante, dessinee par nous.
 *
 *  Un `<select>` natif ne se laisse styler que fermé : la liste qui
 *  s'ouvre est dessinée par le système, avec ses propres couleurs et sa
 *  police. Au milieu d'une interface sombre, elle arrivait en blanc.
 *
 *  Le prix à payer est le clavier et le pointage, que le navigateur
 *  offrait gratuitement : Échap ferme, un clic ailleurs ferme, les
 *  rôles ARIA disent ce que c'est, et le bouton annonce son état.
 */
export default function Choix({
  options, choisi, onChange, etiquette,
}: {
  options: Option[]
  choisi: string
  onChange: (v: string) => void
  etiquette: string
}) {
  const [ouvert, setOuvert] = useState(false)
  const boite = useRef<HTMLDivElement>(null)

  // Fermer au clic ailleurs et à Échap : une liste qu'on ne peut quitter
  // qu'en choisissant est un piège.
  useEffect(() => {
    if (!ouvert) return
    const dehors = (e: MouseEvent) => {
      if (!boite.current?.contains(e.target as Node)) setOuvert(false)
    }
    const touche = (e: KeyboardEvent) => { if (e.key === 'Escape') setOuvert(false) }
    document.addEventListener('mousedown', dehors)
    document.addEventListener('keydown', touche)
    return () => {
      document.removeEventListener('mousedown', dehors)
      document.removeEventListener('keydown', touche)
    }
  }, [ouvert])

  const courant = options.find((o) => o.valeur === choisi)

  return (
    <div ref={boite} className="relative">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={ouvert}
        aria-label={etiquette}
        onClick={() => setOuvert((o) => !o)}
        className="flex w-full items-center gap-2 rounded-carte border border-bordure
                   bg-surface-creuse px-2.5 py-1.5 text-left text-menu text-texte
                   transition-colors duration-200 hover:border-bordure-forte"
      >
        <span className="min-w-0 flex-1 truncate">
          {courant?.libelle ?? '—'}
        </span>
        <LuChevronDown
          size={14}
          className={`shrink-0 text-texte-faible transition-transform duration-200 ${
            ouvert ? 'rotate-180' : ''
          }`}
        />
      </button>

      {ouvert && (
        <ul
          role="listbox"
          aria-label={etiquette}
          // Au-dessus du reste de la page, et detache du bouton : une
          // liste qui pousserait le contenu ferait sauter la mise en
          // page a chaque ouverture.
          //
          // Fond presque opaque, contrairement aux panneaux de verre du
          // reste de l'interface : ceux-ci flottent au-dessus d'un fond
          // de lueurs, celui-ci se pose sur du TEXTE. A 80 % on lisait
          // les libelles de la page au travers des options.
          className="absolute left-0 right-0 top-full z-20 mt-1 max-h-56
                     overflow-y-auto rounded-carte border border-bordure-forte
                     bg-page/95 p-1 shadow-[var(--ombre-carte)] backdrop-blur-xl"
        >
          {options.map((o) => {
            const actif = o.valeur === choisi
            return (
              <li key={o.valeur}>
                <button
                  type="button"
                  role="option"
                  aria-selected={actif}
                  onClick={() => { onChange(o.valeur); setOuvert(false) }}
                  className={`flex w-full items-center gap-2 rounded-carte px-2 py-1.5
                              text-left text-menu transition-colors duration-200 ${
                    actif ? 'text-accent-vif' : 'text-texte-doux hover:bg-survol'
                  }`}
                >
                  <span className="min-w-0 flex-1 truncate">{o.libelle}</span>
                  {actif && <LuCheck size={13} className="shrink-0" />}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
