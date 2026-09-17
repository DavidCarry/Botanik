import {
  LuBellRing, LuDroplet, LuFan, LuLightbulb, LuLock, LuMonitor, LuSun, LuZap,
} from 'react-icons/lu'
import type { IconType } from 'react-icons'
import { useActionneurs } from '../useActionneurs'
import Bloc from './Bloc'

/** L'icone est de la presentation pure : elle n'a rien a faire dans le
 *  registre backend. Un actionneur inconnu retombe sur un symbole
 *  generique plutot que sur un trou. */
const ICONES: Record<string, IconType> = {
  pompe: LuDroplet,
  lumiere: LuSun,
  ventilation: LuFan,
  bipeur: LuBellRing,
  led_rouge: LuLightbulb,
  led_jaune: LuLightbulb,
  led_verte: LuLightbulb,
  ecran: LuMonitor,
}

/** Pilotage manuel.
 *
 *  Presente en lignes simples separees d'un filet, sans cadre ni fond :
 *  le reste de cette colonne repose directement sur le fond, des cartes
 *  encadrees y feraient une piece rapportee.
 *
 *  Sans compte ouvert, l'etat reste PLEINEMENT lisible -- c'est une
 *  information, pas une commande. Seuls les interrupteurs disparaissent,
 *  remplaces par le mot qui dit l'etat. Griser la ligne entiere
 *  reviendrait a cacher ce qu'on est venu voir.
 */
function Etat({ actif, muet }: { actif: boolean; muet: boolean }) {
  if (muet) {
    return (
      <span className="shrink-0 rounded-pilule bg-surface px-2 py-0.5 text-nano font-medium text-texte-faible">
        Inconnu
      </span>
    )
  }
  return (
    <span
      className={`shrink-0 rounded-pilule px-2 py-0.5 text-nano font-medium ${
        actif ? 'bg-accent-voile text-accent-vif' : 'bg-surface text-texte-faible'
      }`}
    >
      {actif ? 'Actif' : 'Arrêté'}
    </span>
  )
}

/** L'etat se lit a la position du curseur, pas seulement a la couleur. */
function Interrupteur({ actif, attendu }: { actif: boolean; attendu: boolean }) {
  return (
    <span
      className={[
        'relative h-5 w-9 shrink-0 rounded-pilule transition-all duration-300',
        actif ? 'bg-accent/55' : 'bg-texte/12',
        attendu ? 'opacity-50' : '',
      ].join(' ')}
    >
      <span
        className={[
          'absolute top-0.5 size-4 rounded-pilule bg-texte transition-all duration-300',
          actif ? 'left-[1.125rem]' : 'left-0.5',
        ].join(' ')}
      />
    </span>
  )
}

export default function Actionneurs({ connecte }: { connecte: boolean }) {
  const { liste, attendus, erreur, basculer } = useActionneurs()

  const mention = erreur ? (
    <span role="alert" className="text-micro text-critique">{erreur}</span>
  ) : !connecte ? (
    <span className="flex items-center gap-1.5 text-micro text-texte-faible">
      <LuLock size={12} className="shrink-0" />
      Connexion requise
    </span>
  ) : undefined

  return (
    // Meme en-tete que les autres sections, par le meme composant : le
    // titre etait redessine ici, a deux pixels pres.
    //
    // En hauteur contrainte, c'est la LISTE qui cede, pas la camera :
    // l'en-tete reste en place et les lignes defilent dessous.
    <Bloc titre="Pilotage" actions={mention} className="md:min-h-0 md:flex-1">
      <div className="divide-y divide-bordure border-y border-bordure
                      md:h-full md:overflow-y-auto">
        {liste.map(({ id, libelle, detail, valeur }) => {
          const Icone = ICONES[id] ?? LuZap
          const attendu = attendus[id]
          // Pendant l'attente, l'interrupteur montre deja la position
          // demandee -- mais en demi-teinte : c'est une intention, pas
          // encore un fait.
          const actif = (attendu?.valeur ?? valeur ?? 0) > 0
          const muet = valeur === null && !attendu

          const contenu = (
            <>
              <Icone
                size={17}
                className={`shrink-0 transition-colors duration-300 ${
                  actif ? 'text-accent-vif' : 'text-texte-faible'
                }`}
              />

              <span className="min-w-0 flex-1 text-left">
                <span className="block truncate text-menu font-medium text-texte">
                  {libelle}
                </span>
                <span className="block truncate text-micro text-texte-faible">
                  {muet ? 'Sans réponse' : detail}
                </span>
              </span>

              {connecte
                ? <Interrupteur actif={actif} attendu={Boolean(attendu)} />
                : <Etat actif={actif} muet={muet} />}
            </>
          )

          const classes = 'flex w-full items-center gap-3 px-1 py-3'

          // Sans compte, la ligne n'est plus un bouton : rien a cliquer,
          // donc rien a annoncer comme cliquable.
          return connecte ? (
            <button
              key={id}
              type="button"
              aria-pressed={actif}
              aria-busy={Boolean(attendu)}
              disabled={muet}
              onClick={() => basculer(id, actif ? 0 : 1)}
              className={`${classes} transition-colors duration-200 ${
                muet ? 'cursor-not-allowed opacity-40' : 'hover:bg-survol'
              }`}
            >
              {contenu}
            </button>
          ) : (
            <div key={id} className={classes}>{contenu}</div>
          )
        })}
      </div>
    </Bloc>
  )
}
