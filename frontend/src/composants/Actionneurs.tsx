import { useState } from 'react'
import { LuDroplet, LuFan, LuLock, LuSun } from 'react-icons/lu'
import type { IconType } from 'react-icons'
import { commander } from '../api'

type Actionneur = {
  id: string
  libelle: string
  detail: string
  icone: IconType
}

const ACTIONNEURS: Actionneur[] = [
  { id: 'pompe', libelle: 'Arrosage', detail: '20 mL par impulsion', icone: LuDroplet },
  { id: 'lumiere', libelle: 'Éclairage', detail: 'LED horticole', icone: LuSun },
  { id: 'ventilation', libelle: 'Ventilation', detail: 'Circulation d’air', icone: LuFan },
]

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
 *  La commande est enregistree en base ; le sens retour de MQTT vers le
 *  materiel reste a cabler. */
export default function Actionneurs({ connecte }: { connecte: boolean }) {
  const [actifs, setActifs] = useState<Record<string, boolean>>({})
  const [erreur, setErreur] = useState<string | null>(null)

  const basculer = async (id: string) => {
    if (!connecte) return
    const suivant = !actifs[id]
    setActifs((a) => ({ ...a, [id]: suivant }))
    try {
      await commander(id, suivant ? 1 : 0)
      setErreur(null)
    } catch {
      // On revient en arriere : l'interrupteur ne doit pas affirmer un
      // etat que le serveur n'a pas accepte.
      setActifs((a) => ({ ...a, [id]: !suivant }))
      setErreur('Commande refusée')
    }
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between gap-3 px-1 pb-2">
        <span className="text-micro font-medium uppercase tracking-[0.14em] text-texte-faible">
          Pilotage
        </span>
        {!connecte && (
          <span className="flex items-center gap-1.5 text-micro text-texte-faible">
            <LuLock size={12} className="shrink-0" />
            Connexion requise
          </span>
        )}
        {erreur && (
          <span role="alert" className="text-micro text-critique">{erreur}</span>
        )}
      </div>

      <div className="divide-y divide-bordure border-y border-bordure">
        {ACTIONNEURS.map(({ id, libelle, detail, icone: Icone }) => {
          const actif = actifs[id] ?? false
          return (
            <button
              key={id}
              type="button"
              aria-pressed={actif}
              disabled={!connecte}
              onClick={() => basculer(id)}
              className={[
                'flex w-full items-center gap-3 px-1 py-3 text-left transition-colors duration-200',
                connecte ? 'hover:bg-texte/[0.03]' : 'cursor-not-allowed opacity-40',
              ].join(' ')}
            >
              <Icone
                size={17}
                className={`shrink-0 transition-colors duration-300 ${
                  actif ? 'text-accent-vif' : 'text-texte-faible'
                }`}
              />

              <span className="min-w-0 flex-1">
                <span className="block truncate text-menu font-medium text-texte">
                  {libelle}
                </span>
                <span className="block truncate text-micro text-texte-faible">
                  {detail}
                </span>
              </span>

              {/* L'etat se lit a la position du curseur, pas seulement a
                  la couleur. */}
              <span
                className={[
                  'relative h-5 w-9 shrink-0 rounded-pilule transition-colors duration-300',
                  actif ? 'bg-accent/55' : 'bg-texte/12',
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
