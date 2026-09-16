import {
  LuBellRing, LuDroplet, LuFan, LuHand, LuLightbulb, LuLock, LuMonitor, LuSun, LuZap,
} from 'react-icons/lu'
import type { IconType } from 'react-icons'
import { useActionneurs } from '../useActionneurs'

/** L'icone est de la presentation pure : elle n'a rien a faire dans le
 *  registre backend. Un actionneur inconnu retombe sur un symbole
 *  generique plutot que sur un trou. */
const ICONES: Record<string, IconType> = {
  pompe: LuDroplet,
  lumiere: LuSun,
  ventilation: LuFan,
  bipeur: LuBellRing,
  leds: LuLightbulb,
  ecran: LuMonitor,
}

/** Pilotage manuel.
 *
 *  Presente en lignes simples separees d'un filet, sans cadre ni fond :
 *  le reste de cette colonne repose directement sur le fond, des cartes
 *  encadrees y feraient une piece rapportee.
 *
 *  Sans compte ouvert, les commandes restent visibles mais inertes --
 *  montrer ce qui existe vaut mieux que de le cacher, et le serveur
 *  refuse de toute facon toute commande non authentifiee.
 *
 *  Reprendre la main pose un verrou : le modele s'abstient quelques
 *  minutes. Le decompte est affiche, faute de quoi on ne comprendrait
 *  pas pourquoi l'interrupteur cesse soudain de bouger tout seul.
 */
const minutes = (s: number) =>
  s >= 60 ? `${Math.ceil(s / 60)} min` : `${s} s`
export default function Actionneurs({ connecte }: { connecte: boolean }) {
  const { liste, attendus, erreur, basculer } = useActionneurs()

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between gap-3 px-1 pb-2">
        <span className="text-micro font-medium uppercase tracking-[0.14em] text-texte-faible">
          Pilotage
        </span>
        {erreur ? (
          <span role="alert" className="text-micro text-critique">{erreur}</span>
        ) : !connecte && (
          <span className="flex items-center gap-1.5 text-micro text-texte-faible">
            <LuLock size={12} className="shrink-0" />
            Connexion requise
          </span>
        )}
      </div>

      <div className="divide-y divide-bordure border-y border-bordure">
        {liste.map(({ id, libelle, detail, valeur, pilote, verrou_s }) => {
          const Icone = ICONES[id] ?? LuZap
          const attendu = attendus[id]
          // Pendant l'attente, l'interrupteur montre deja la position
          // demandee -- mais en demi-teinte : c'est une intention, pas
          // encore un fait.
          const actif = (attendu?.valeur ?? valeur ?? 0) > 0
          const muet = valeur === null && !attendu

          return (
            <button
              key={id}
              type="button"
              aria-pressed={actif}
              aria-busy={Boolean(attendu)}
              disabled={!connecte || muet}
              onClick={() => basculer(id, actif ? 0 : 1)}
              className={[
                'flex w-full items-center gap-3 px-1 py-3 text-left transition-colors duration-200',
                connecte && !muet
                  ? 'hover:bg-texte/[0.03]'
                  : 'cursor-not-allowed opacity-40',
              ].join(' ')}
            >
              <Icone
                size={17}
                className={`shrink-0 transition-colors duration-300 ${
                  actif ? 'text-accent-vif' : 'text-texte-faible'
                }`}
              />

              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5">
                  <span className="truncate text-menu font-medium text-texte">
                    {libelle}
                  </span>
                  {/* Dire qui commande : sans cela, on ne saurait pas
                      pourquoi un interrupteur revient tout seul a sa
                      position. */}
                  {pilote === 'ia' && verrou_s === 0 && (
                    <span className="shrink-0 rounded-pilule bg-accent-voile px-1.5 py-px text-[0.55rem] font-medium tracking-[0.08em] text-accent-vif">
                      IA
                    </span>
                  )}
                  {/* Le verrou remplace la marque du modele : c'est bien
                      la main qui commande, pas lui. */}
                  {verrou_s > 0 && (
                    <span className="flex shrink-0 items-center gap-1 rounded-pilule bg-texte/[0.07] px-1.5 py-px text-[0.55rem] font-medium tracking-[0.08em] text-texte-doux">
                      <LuHand size={9} />
                      {minutes(verrou_s)}
                    </span>
                  )}
                </span>
                <span className="block truncate text-micro text-texte-faible">
                  {muet ? 'Sans réponse' : detail}
                </span>
              </span>

              {/* L'etat se lit a la position du curseur, pas seulement a
                  la couleur. */}
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
            </button>
          )
        })}
      </div>
    </div>
  )
}
