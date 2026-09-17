import { useState } from 'react'
import { LuMonitor } from 'react-icons/lu'
import type { Contenu } from '../api'
import { LIBELLE_BILLE } from '../libelles'
import { useMesures } from '../useMesures'
import Modale from './Modale'

/** Largeur et hauteur de l'afficheur, en caractères. Les mêmes que
 *  côté serveur : l'aperçu ne vaut que s'il coupe au même endroit. */
const COLONNES = 16
const LIGNES = 2

/** Le texte tel que l'afficheur saura le dessiner.
 *
 *  Un HD44780 ne connaît pas les accents : « Température » y sortirait
 *  en caractères japonais, et le driver les retire donc avant d'écrire.
 *  L'aperçu doit faire pareil, sinon il promet un mot que l'écran ne
 *  montrera pas. */
const pourEcran = (texte: string) =>
  texte.normalize('NFKD').replace(/\p{Diacritic}/gu, '')
    .replace(/[^ -~]/g, ' ')

/** Ce que l'écran montrera, tel qu'il le montrera.
 *
 *  Un afficheur de seize caractères coupe sans prévenir : montrer les
 *  deux lignes exactes évite d'écrire un texte qu'on croit entier et de
 *  découvrir devant la serre qu'il manque la fin. */
function Apercu({ lignes }: { lignes: string[] }) {
  return (
    <div className="rounded-carte border border-bordure bg-surface-creuse p-3">
      <span className="mb-2 block text-nano uppercase tracking-etiquette text-texte-faible">
        Sur l’écran
      </span>
      <div className="space-y-1 font-mono text-menu leading-snug text-accent-vif">
        {Array.from({ length: LIGNES }, (_, i) => (
          <div key={i} className="whitespace-pre">
            {pourEcran(lignes[i] ?? '').padEnd(COLONNES, ' ').slice(0, COLONNES)}
          </div>
        ))}
      </div>
    </div>
  )
}

/** Choix de ce que l'afficheur montre.
 *
 *  Deux façons de le dire : suivre une mesure, ou écrire un texte. La
 *  première est une INTENTION -- « la température » -- et l'écran suit
 *  la valeur ensuite ; la seconde est figée, c'est tout l'intérêt.
 *
 *  Une fenêtre plutôt qu'un réglage dans la liste : quatre capteurs, un
 *  champ de texte et un aperçu ne tiennent pas sur une ligne de tableau
 *  de bord, et les y tasser aurait abîmé le reste.
 */
export default function Affichage({
  actuel, onValider, onFermer,
}: {
  actuel: Contenu | null | undefined
  onValider: (contenu: Contenu) => void
  onFermer: () => void
}) {
  const { capteurs } = useMesures()

  const [mode, setMode] = useState<'mesure' | 'texte'>(actuel?.mode ?? 'mesure')
  const [capteur, setCapteur] = useState(
    actuel?.mode === 'mesure' ? actuel.capteur : '',
  )
  const [texte, setTexte] = useState(actuel?.mode === 'texte' ? actuel.texte : '')

  const liste = capteurs ?? []
  const choisi = liste.find((c) => c.id === capteur) ?? liste[0]

  // L'aperçu compose exactement comme le service : libellé du registre,
  // puis valeur et unité.
  const lignes = mode === 'texte'
    ? [texte.slice(0, COLONNES), texte.slice(COLONNES, COLONNES * LIGNES)]
    : choisi
      ? [choisi.libelle,
         choisi.mesure ? `${choisi.mesure.valeur} ${choisi.unite}` : 'en attente']
      : ['', '']

  const valide = mode === 'texte' ? texte.trim().length > 0 : Boolean(choisi)

  return (
    <Modale
      titre="Affichage de l’écran"
      sousTitre="Ce que le LCD de la serre montre"
      icone={<LuMonitor size={17} />}
      onFermer={onFermer}
    >
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-2">
          {liste.map((c) => {
            const actif = mode === 'mesure' && choisi?.id === c.id
            return (
              <button
                key={c.id}
                type="button"
                aria-pressed={actif}
                onClick={() => { setMode('mesure'); setCapteur(c.id) }}
                className={`rounded-carte border px-3 py-2 text-left text-menu
                            transition-colors duration-200 ${
                  actif
                    ? 'border-bordure-forte bg-accent-voile text-accent-vif'
                    : 'border-bordure text-texte-doux hover:text-texte'
                }`}
              >
                {LIBELLE_BILLE[c.id] ?? c.libelle}
              </button>
            )
          })}
        </div>

        <div>
          <label className="mb-1.5 flex items-center gap-2 text-micro text-texte-faible">
            <input
              type="radio"
              checked={mode === 'texte'}
              onChange={() => setMode('texte')}
              className="accent-[var(--accent)]"
            />
            Texte libre
          </label>
          <input
            type="text"
            value={texte}
            maxLength={COLONNES * LIGNES}
            placeholder="Votre message"
            onChange={(e) => { setTexte(e.target.value); setMode('texte') }}
            className="w-full rounded-carte border border-bordure bg-surface-creuse
                       px-3 py-2 text-menu text-texte outline-none
                       placeholder:text-texte-faible focus:border-bordure-forte"
          />
        </div>

        <Apercu lignes={lignes} />

        <button
          type="button"
          disabled={!valide}
          onClick={() => onValider(
            mode === 'texte'
              ? { mode: 'texte', texte: texte.trim() }
              : { mode: 'mesure', capteur: choisi!.id },
          )}
          className="w-full rounded-carte border border-bordure bg-accent-voile
                     py-2 text-menu font-medium text-accent-vif transition-colors
                     duration-200 hover:border-bordure-forte
                     disabled:cursor-not-allowed disabled:opacity-40"
        >
          Afficher
        </button>
      </div>
    </Modale>
  )
}
