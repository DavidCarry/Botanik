import type { ActionRegle } from '../api'
import Choix from './Choix'

/** Le style des champs de saisie des réglages.
 *
 *  Exporté d'ici parce que les deux pages de réglage l'utilisent : les
 *  bornes pour leur valeur chiffrée, les visages pour le message à
 *  afficher. Deux copies auraient fini par diverger d'un pixel. */
export const CHAMP =
  'w-full rounded-carte border border-bordure bg-surface-creuse px-2.5 py-1.5 ' +
  'text-menu text-texte outline-none focus:border-bordure-forte'

/** Ce que la serre fait quand un déclencheur s'active.
 *
 *  Le même éditeur pour les deux sortes de règles : une borne franchie
 *  et une personne reconnue aboutissent à la même action, et doivent
 *  donc se régler de la même façon. C'est aussi ce qui garantit qu'un
 *  actionneur ajouté apparaît dans les deux pages d'un coup.
 *
 *  `permetAucune` distingue les deux cas. Une borne peut n'avoir aucune
 *  action -- on surveille la température sans rien pouvoir y faire. Un
 *  visage sans action ne serait pas une règle du tout : on la retire.
 */
export default function EditeurAction({
  action, actionneurs, etiquette, permetAucune = true, onChange,
}: {
  action: ActionRegle | null
  actionneurs: { id: string; libelle: string }[]
  etiquette: string
  permetAucune?: boolean
  onChange: (a: ActionRegle | null) => void
}) {
  // On isole chaque forme : le type d'une action dépend de son genre, et
  // TypeScript ne le devine pas au milieu d'un JSX.
  const surActionneur = action?.genre === 'actionneur' ? action : null
  const surEcran = action?.genre === 'ecran' ? action : null

  const changer = (nouveau: string) => {
    if (nouveau === 'aucun') return onChange(null)
    if (nouveau === 'ecran') return onChange({ genre: 'ecran', texte: '' })
    onChange({ genre: 'actionneur', cible: nouveau, valeur: 1 })
  }

  return (
    <div className="space-y-2">
      <Choix
        etiquette={etiquette}
        choisi={surActionneur ? surActionneur.cible : (action?.genre ?? 'aucun')}
        onChange={changer}
        // L'afficheur n'apparait PAS parmi les actionneurs : le mettre
        // en marche sans lui dire quoi montrer n'a pas de sens, et deux
        // entrées pour le même matériel obligeaient à deviner laquelle
        // fait quoi.
        options={[
          ...(permetAucune
            ? [{ valeur: 'aucun', libelle: 'Ne rien faire (alerter seulement)' }]
            : []),
          ...actionneurs
            .filter((a) => a.id !== 'ecran')
            .map((a) => ({ valeur: a.id, libelle: a.libelle })),
          { valeur: 'ecran', libelle: 'Afficher un message à l’écran' },
        ]}
      />

      {surActionneur && (
        <div className="flex gap-0.5 rounded-pilule border border-bordure bg-surface-creuse p-0.5">
          {[1, 0].map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={surActionneur.valeur === v}
              onClick={() => onChange({
                genre: 'actionneur', cible: surActionneur.cible, valeur: v,
              })}
              className={`flex-1 rounded-pilule px-2 py-1 text-micro font-medium
                          transition-colors duration-200 ${
                surActionneur.valeur === v
                  ? 'bg-accent-voile text-accent-vif'
                  : 'text-texte-faible hover:text-texte-doux'
              }`}
            >
              {v ? 'Allumer' : 'Éteindre'}
            </button>
          ))}
        </div>
      )}

      {surEcran && (
        <input
          type="text"
          maxLength={32}
          value={surEcran.texte}
          placeholder="Message sur l’écran"
          onChange={(e) => onChange({ genre: 'ecran', texte: e.target.value })}
          className={CHAMP}
        />
      )}
    </div>
  )
}
