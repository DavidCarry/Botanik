import { useEffect, useState, type ReactNode } from 'react'
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

/* Les deux boutons que portent a la fois une carte de grandeur et le
 * reglage de clarte : valider, et revenir a ce qui est enregistre. */
const VALIDER = `flex items-center gap-1.5 rounded-pilule border border-bordure
                 bg-accent-voile px-3 py-1 text-micro font-medium text-accent-vif
                 transition-colors duration-200 hover:border-bordure-forte
                 disabled:cursor-not-allowed disabled:border-bordure
                 disabled:bg-transparent disabled:text-texte-faible`

const DEFAIRE = `rounded-pilule p-1.5 text-texte-faible transition-colors
                 duration-200 hover:bg-survol hover:text-texte`

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

/** À partir de quelle clarté la lumière compte dans le cumul du jour.
 *
 *  Ce n'est PAS une borne : rien ne se déclenche quand on la franchit.
 *  C'est la définition de ce qu'on compte — sans elle on réglait « douze
 *  heures de lumière » sans pouvoir dire douze heures de quoi.
 *
 *  Et elle ne concerne que le cumul. Le jugement « luminosité trop
 *  faible » du réseau, lui, a été appris avec sa propre valeur : les
 *  deux peuvent différer, et seul un réentraînement les réaligne.
 */
function ClarteUtile({
  valeur, unite, occupe, onEnregistrer,
}: {
  valeur: number
  unite: string
  occupe: boolean
  onEnregistrer: (utile: number) => void
}) {
  // La saisie est gardée en texte et non en nombre : un champ vidé pour
  // être retapé vaut '' le temps de la frappe, ce qu'un `number` ne sait
  // pas représenter sans se transformer en zéro sous le doigt.
  //
  // Elle part de la valeur du serveur et ne la resynchronise jamais
  // elle-même : l'appelant donne à ce composant une `key` tirée de cette
  // valeur, donc une valeur qui change le remonte avec une saisie
  // neuve. C'est la même promesse que pour les bornes -- le serveur fait
  // foi -- obtenue sans effet qui rappellerait `setState` au rendu
  // suivant.
  const [saisie, setSaisie] = useState(String(valeur))

  const nombre = Number(saisie)
  const valide = saisie.trim() !== '' && Number.isFinite(nombre)
  const modifie = valide && nombre !== valeur

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-carte
                    border border-bordure bg-surface-creuse p-3">
      <div className="min-w-0 flex-1">
        <span className="block text-nano uppercase tracking-etiquette text-texte-faible">
          Compte à partir de
        </span>
        <p className="mt-1 text-nano leading-relaxed text-texte-faible">
          Sous cette clarté, le temps qui passe ne compte pas dans le cumul.
        </p>
      </div>

      <label className="flex items-center gap-2">
        <input
          type="number"
          step="any"
          value={saisie}
          onChange={(e) => setSaisie(e.target.value)}
          aria-label="Clarté à partir de laquelle la lumière compte"
          className={CHAMP}
        />
        <span className="shrink-0 text-micro text-texte-faible">{unite}</span>
      </label>

      {modifie && (
        <button
          type="button"
          onClick={() => setSaisie(String(valeur))}
          aria-label="Abandonner la modification de la clarté utile"
          className={DEFAIRE}
        >
          <LuRotateCcw size={14} />
        </button>
      )}
      <button
        type="button"
        disabled={!modifie || occupe}
        onClick={() => onEnregistrer(nombre)}
        className={VALIDER}
      >
        <LuCheck size={13} />
        {modifie ? 'Enregistrer' : 'À jour'}
      </button>
    </div>
  )
}

/** Une grandeur et sa règle, modifiable puis enregistrable. */
function Carte({
  grandeur, actionneurs, occupe, onEnregistrer, onRetirer, enTete,
}: {
  grandeur: GrandeurReglee
  actionneurs: { id: string; libelle: string }[]
  occupe: boolean
  onEnregistrer: (bas: BorneRegle, haut: BorneRegle) => void
  onRetirer: () => void
  /** Posé entre l'intitulé et les deux bornes. Ne sert qu'à « Lumière
   *  reçue », seule grandeur à porter un réglage qui n'est pas une
   *  borne : le cas particulier reste dans la liste, pas ici. */
  enTete?: ReactNode
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
              className={DEFAIRE}
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
            className={VALIDER}
          >
            <LuCheck size={13} />
            {modifie ? 'Enregistrer' : 'À jour'}
          </button>
        </span>
      </div>

      {enTete}

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
  const {
    reglages, occupe, erreur, enregistrer, retirer, reglerLumiereUtile,
  } = useRegles()

  // L'unité du seuil de clarté est celle du CAPTEUR de luminosité, pas
  // celle du cumul : on y saisit une clarté, pas des heures. Le repli
  // sert au cas où ce capteur serait désactivé — le cumul, lui, reste
  // réglable.
  const uniteClarte =
    reglages.grandeurs.find((g) => g.id === 'luminosite')?.unite ?? '%'

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
            enTete={g.id === 'eclairement_jour' ? (
              <ClarteUtile
                key={reglages.lumiere_utile}
                valeur={reglages.lumiere_utile}
                unite={uniteClarte}
                occupe={occupe === 'lumiere_utile'}
                onEnregistrer={reglerLumiereUtile}
              />
            ) : undefined}
          />
        ))}
      </div>
    </Bloc>
  )
}
