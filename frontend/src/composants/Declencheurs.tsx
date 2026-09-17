import { useEffect, useState } from 'react'
import { LuCheck, LuRotateCcw, LuScanFace, LuTrash2, LuUsers } from 'react-icons/lu'
import type { ActionRegle, Sujet } from '../api'
import { useReglagesVisages } from '../useVisages'
import Bloc from './Bloc'
import EditeurAction from './EditeurAction'

/** Un sujet, et ce que la serre fait en le voyant. */
function Ligne({
  sujet, regle, actionneurs, occupe, onEnregistrer, onRetirer,
}: {
  sujet: Sujet
  regle: ActionRegle | null
  actionneurs: { id: string; libelle: string }[]
  occupe: boolean
  onEnregistrer: (a: ActionRegle) => void
  onRetirer: () => void
}) {
  const [action, setAction] = useState<ActionRegle | null>(regle)

  // La version du serveur fait foi : dès qu'elle change, on reprend la
  // sienne plutôt que de garder une saisie devenue fausse.
  const signature = JSON.stringify(regle)
  useEffect(() => {
    setAction(regle)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature])

  const modifie = JSON.stringify(action) !== signature
  const complet = action !== null
    && (action.genre !== 'ecran' || action.texte.trim() !== '')

  return (
    // Une carte par sujet, et non des lignes filetées : la page est
    // large, et une liste pleine largeur étirait chaque sélecteur
    // d'action sur tout l'écran pour trois mots.
    <div className="space-y-2.5 rounded-carte border border-bordure p-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {sujet.references === undefined
          ? <LuUsers size={14} className="shrink-0 text-texte-faible" />
          : <LuScanFace size={14} className="shrink-0 text-accent-vif" />}
        <span className="text-menu font-medium text-texte">{sujet.libelle}</span>
        <span className="text-micro text-texte-faible">
          {sujet.detail ?? `${sujet.references} référence${
            (sujet.references ?? 0) > 1 ? 's' : ''}`}
        </span>

        <span className="ml-auto flex items-center gap-2">
          {modifie && (
            <button
              type="button"
              onClick={() => setAction(regle)}
              aria-label={`Abandonner les modifications de ${sujet.libelle}`}
              className="rounded-pilule p-1.5 text-texte-faible transition-colors
                         duration-200 hover:bg-survol hover:text-texte"
            >
              <LuRotateCcw size={14} />
            </button>
          )}
          {regle && (
            <button
              type="button"
              onClick={onRetirer}
              disabled={occupe}
              aria-label={`Retirer le déclencheur de ${sujet.libelle}`}
              className="rounded-pilule p-1.5 text-texte-faible transition-colors
                         duration-200 hover:bg-survol hover:text-critique
                         disabled:opacity-40"
            >
              <LuTrash2 size={14} />
            </button>
          )}
          <button
            type="button"
            disabled={!modifie || !complet || occupe}
            onClick={() => action && onEnregistrer(action)}
            className="flex items-center gap-1.5 rounded-pilule border border-bordure
                       bg-accent-voile px-3 py-1 text-micro font-medium text-accent-vif
                       transition-colors duration-200 hover:border-bordure-forte
                       disabled:cursor-not-allowed disabled:border-bordure
                       disabled:bg-transparent disabled:text-texte-faible"
          >
            <LuCheck size={13} />
            {modifie ? 'Enregistrer' : 'À jour'}
          </button>
        </span>
      </div>

      <EditeurAction
        action={action}
        actionneurs={actionneurs}
        etiquette={`Action quand ${sujet.libelle.toLowerCase()} est là`}
        // Un visage sans action ne serait pas une règle : on la retire.
        permetAucune={false}
        onChange={setAction}
      />
    </div>
  )
}

/** Ce que la serre fait quand elle voit quelqu'un.
 *
 *  Même forme d'action que les bornes, et c'est voulu : un visage
 *  reconnu et un seuil franchi déclenchent exactement les mêmes choses.
 *  Seul le déclencheur change.
 *
 *  Les deux premiers sujets ne désignent personne en particulier et sont
 *  toujours là ; les suivants sont les personnes apprises. On les ajoute
 *  et on les retire avec `apprendre_visages.py`, pas d'ici : effacer un
 *  visage d'un clic obligerait à en reprendre une photo.
 */
export default function Declencheurs() {
  const { reglages, occupe, erreur, enregistrer, retirer } = useReglagesVisages()

  const sujets = [...reglages.speciaux, ...reglages.personnes]

  return (
    <Bloc
      titre="Visages"
      actions={erreur
        ? <span role="alert" className="text-micro text-critique">{erreur}</span>
        : <span className="text-micro text-texte-faible">
            {reglages.personnes.length === 0
              ? 'aucune personne apprise'
              : `${reglages.personnes.length} personne${
                  reglages.personnes.length > 1 ? 's' : ''} connue${
                  reglages.personnes.length > 1 ? 's' : ''}`}
          </span>}
      className="h-full md:min-h-0"
    >
      <div className="grid h-full content-start gap-3 overflow-y-auto pr-1
                      sm:grid-cols-2 xl:grid-cols-3">
        {sujets.length === 0 ? (
          <p className="text-micro text-texte-faible">Lecture des visages…</p>
        ) : sujets.map((s) => (
          <Ligne
            key={s.id}
            sujet={s}
            regle={reglages.regles[s.id] ?? null}
            actionneurs={reglages.actionneurs}
            occupe={occupe === s.id}
            onEnregistrer={(a) => enregistrer(s.id, a)}
            onRetirer={() => retirer(s.id)}
          />
        ))}
      </div>
    </Bloc>
  )
}
