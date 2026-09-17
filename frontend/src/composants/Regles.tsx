import { useEffect, useState } from 'react'
import { LuBrain, LuCheck, LuRotateCcw, LuTrash2 } from 'react-icons/lu'
import type { BorneRegle, GrandeurReglee, ModeBorne } from '../api'
import { useRegles } from '../useRegles'
import Bloc from './Bloc'
import EditeurAction, { CHAMP } from './EditeurAction'

/** Les trois façons de poser une borne.
 *
 *  « IA » ne copie pas le seuil appris : elle le SUIT. Il se déplace
 *  avec la chaleur et la lumière, et la borne avec lui. Copier un
 *  nombre l'aurait figé au moment du clic, ce qui n'est pas la même
 *  promesse. */
const MODES: { valeur: ModeBorne; libelle: string }[] = [
  { valeur: 'ia', libelle: 'IA' },
  { valeur: 'manuel', libelle: 'Manuel' },
  { valeur: 'aucun', libelle: 'Aucune' },
]

const VIDE: BorneRegle = { mode: 'aucun', valeur: null, action: null }

/** Un côté d'une grandeur : où passe la borne, et ce qui se passe quand
 *  elle est franchie. */
function Cote({
  titre, borne, apprise, unite, actionneurs, onChange,
}: {
  titre: string
  borne: BorneRegle
  apprise: number | null | undefined
  unite: string
  actionneurs: { id: string; libelle: string }[]
  onChange: (b: BorneRegle) => void
}) {
  return (
    <div className="space-y-2.5 rounded-carte border border-bordure p-3">
      <span className="block text-nano uppercase tracking-etiquette text-texte-faible">
        {titre}
      </span>

      <div className="flex gap-0.5 rounded-pilule border border-bordure bg-surface-creuse p-0.5">
        {MODES.map((m) => (
          <button
            key={m.valeur}
            type="button"
            aria-pressed={borne.mode === m.valeur}
            onClick={() => onChange({ ...borne, mode: m.valeur })}
            className={`flex-1 rounded-pilule px-2 py-1 text-micro font-medium
                        transition-colors duration-200 ${
              borne.mode === m.valeur
                ? 'bg-accent-voile text-accent-vif'
                : 'text-texte-faible hover:text-texte-doux'
            }`}
          >
            {m.libelle}
          </button>
        ))}
      </div>

      {borne.mode === 'manuel' && (
        <label className="flex items-center gap-2">
          <input
            type="number"
            step="any"
            value={borne.valeur ?? ''}
            onChange={(e) => onChange({
              ...borne,
              valeur: e.target.value === '' ? null : Number(e.target.value),
            })}
            className={CHAMP}
          />
          <span className="shrink-0 text-micro text-texte-faible">{unite}</span>
        </label>
      )}

      {borne.mode === 'ia' && (
        <p className="flex items-center gap-1.5 text-micro text-texte-faible">
          <LuBrain size={12} className="shrink-0" />
          {apprise == null
            ? 'le réseau n’a rien appris de ce côté'
            : <>suit le seuil appris — <span className="tabular-nums text-texte-doux">
                {apprise} {unite}</span> en ce moment</>}
        </p>
      )}

      {borne.mode !== 'aucun' && (
        <EditeurAction
          action={borne.action}
          actionneurs={actionneurs}
          etiquette={`Action quand ${titre.toLowerCase()}`}
          onChange={(action) => onChange({ ...borne, action })}
        />
      )}
    </div>
  )
}

/** Une grandeur et sa règle, modifiable puis enregistrable. */
function Carte({
  grandeur, actionneurs, occupe, onEnregistrer, onRetirer,
}: {
  grandeur: GrandeurReglee
  actionneurs: { id: string; libelle: string }[]
  occupe: boolean
  onEnregistrer: (bas: BorneRegle, haut: BorneRegle) => void
  onRetirer: () => void
}) {
  const depuisServeur = (): [BorneRegle, BorneRegle] => [
    grandeur.regle?.bas ?? VIDE,
    grandeur.regle?.haut ?? VIDE,
  ]

  const [bas, setBas] = useState<BorneRegle>(depuisServeur()[0])
  const [haut, setHaut] = useState<BorneRegle>(depuisServeur()[1])

  // La version du serveur fait foi : dès qu'elle change -- après un
  // enregistrement, ou parce que les seuils appris ont bougé -- on
  // reprend la sienne plutôt que de garder une saisie devenue fausse.
  const signature = JSON.stringify(grandeur.regle)
  useEffect(() => {
    setBas(grandeur.regle?.bas ?? VIDE)
    setHaut(grandeur.regle?.haut ?? VIDE)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature])

  const modifie = JSON.stringify([bas, haut]) !== JSON.stringify(depuisServeur())

  return (
    <div className="space-y-3 border-t border-bordure pt-4 first:border-0 first:pt-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-menu font-medium text-texte">{grandeur.libelle}</span>
        <span className="text-micro text-texte-faible">{grandeur.unite}</span>

        <span className="ml-auto flex items-center gap-2">
          {/* Revenir a ce qui est enregistre. Sans cela, une saisie
              qu'on regrette ne se defaisait qu'en rechargeant la page
              -- et on ne savait plus ce qui s'appliquait vraiment. */}
          {modifie && (
            <button
              type="button"
              onClick={() => {
                const [b, h] = depuisServeur()
                setBas(b)
                setHaut(h)
              }}
              aria-label={`Abandonner les modifications de ${grandeur.libelle}`}
              className="rounded-pilule p-1.5 text-texte-faible transition-colors
                         duration-200 hover:bg-survol hover:text-texte"
            >
              <LuRotateCcw size={14} />
            </button>
          )}
          {grandeur.regle && (
            <button
              type="button"
              onClick={onRetirer}
              disabled={occupe}
              aria-label={`Retirer la règle de ${grandeur.libelle}`}
              className="rounded-pilule p-1.5 text-texte-faible transition-colors
                         duration-200 hover:bg-survol hover:text-critique
                         disabled:opacity-40"
            >
              <LuTrash2 size={14} />
            </button>
          )}
          <button
            type="button"
            disabled={!modifie || occupe}
            onClick={() => onEnregistrer(bas, haut)}
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

      <div className="grid gap-3 sm:grid-cols-2">
        <Cote
          titre="Sous la borne basse"
          borne={bas}
          apprise={grandeur.seuil_ia?.bas}
          unite={grandeur.unite}
          actionneurs={actionneurs}
          onChange={setBas}
        />
        <Cote
          titre="Au-dessus de la borne haute"
          borne={haut}
          apprise={grandeur.seuil_ia?.haut}
          unite={grandeur.unite}
          actionneurs={actionneurs}
          onChange={setHaut}
        />
      </div>
    </div>
  )
}

/** Le réglage de la serre : où passent les bornes, et ce qu'elle fait
 *  quand elles sont franchies.
 *
 *  C'est la SEULE source des actions. Il n'y a plus aucune règle écrite
 *  dans le code : une grandeur laissée sans règle ne déclenche rien, ni
 *  alerte ni commande. Le réseau, lui, continue d'apprendre où passent
 *  les frontières -- une borne réglée sur « IA » le suit.
 */
export default function Regles() {
  const { reglages, occupe, erreur, enregistrer, retirer } = useRegles()

  return (
    <Bloc
      titre="Réglages"
      actions={erreur
        ? <span role="alert" className="text-micro text-critique">{erreur}</span>
        : <span className="text-micro text-texte-faible">
            Une grandeur sans règle ne déclenche rien
          </span>}
      className="h-full md:min-h-0"
    >
      <div className="h-full space-y-4 overflow-y-auto pr-1">
        {reglages.grandeurs.length === 0 ? (
          <p className="text-micro text-texte-faible">Lecture des réglages…</p>
        ) : reglages.grandeurs.map((g) => (
          <Carte
            key={g.id}
            grandeur={g}
            actionneurs={reglages.actionneurs}
            occupe={occupe === g.id}
            onEnregistrer={(bas, haut) => enregistrer(g.id, bas, haut)}
            onRetirer={() => retirer(g.id)}
          />
        ))}
      </div>
    </Bloc>
  )
}
