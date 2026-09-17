import {
  LuBellRing, LuCircleDot, LuDroplet, LuFan, LuLightbulb, LuMonitor,
  LuSun, LuTriangleAlert, LuZap,
} from 'react-icons/lu'
import type { IconType } from 'react-icons'
import { depuis } from '../format'
import { useEvenements } from '../useEvenements'

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

const NOMS: Record<string, string> = {
  pompe: 'Arrosage',
  lumiere: 'Éclairage',
  ventilation: 'Ventilation',
  bipeur: 'Alerte sonore',
  led_rouge: 'LED rouge',
  led_jaune: 'LED jaune',
  led_verte: 'LED verte',
  ecran: 'Écran',
}

/** Qui a decide. La distinction est le seul moyen de relire apres coup
 *  ce que la serre a fait seule, et de le separer de ce qu'on a fait
 *  soi-meme. */
const ORIGINES: Record<string, { libelle: string; classe: string }> = {
  manuel: { libelle: 'manuel', classe: 'text-texte-faible' },
  regle: { libelle: 'règle', classe: 'text-accent-vif' },
}

/** Journal melant les alertes et les commandes.
 *
 *  Les deux dans le meme fil, parce qu'ils se lisent ensemble :
 *  « sol trop sec détecté », puis « arrosage activé », puis « sol trop
 *  sec levé ». Separes en deux listes, la causalite disparaitrait.
 */
export default function Evenements() {
  const liste = useEvenements()

  if (liste === null) {
    return <p className="text-micro text-texte-faible">Lecture du journal…</p>
  }
  if (liste.length === 0) {
    return (
      <p className="grid h-full place-items-center text-micro text-texte-faible">
        Rien à signaler
      </p>
    )
  }

  return (
    // Meme trame que le pilotage et les seuils du modele : des lignes
    // separees d'un filet, sans carte ni fond. Un survol arrondi au
    // milieu d'une liste filetee cassait cet alignement.
    <ul className="h-full divide-y divide-bordure overflow-y-auto">
      {liste.map((e, i) => (
        <li
          key={`${e.ts}-${e.sujet}-${i}`}
          className="flex items-center gap-2.5 px-1 py-2 transition-colors hover:bg-survol"
        >
          {e.genre === 'alerte' ? (
            <>
              <LuTriangleAlert
                size={14}
                className={`shrink-0 ${
                  e.ouverture
                    ? e.humaine ? 'text-critique' : 'text-attention'
                    : 'text-bon'
                }`}
              />
              <span className="min-w-0 flex-1 truncate text-micro text-texte">
                {e.libelle}
                <span className="ml-1.5 text-texte-doux">
                  {e.ouverture ? 'détecté' : 'levé'}
                </span>
              </span>
              <span className="shrink-0 text-nano font-medium text-texte-faible">
                alerte
              </span>
            </>
          ) : (
            <>
              {(() => {
                const Icone = ICONES[e.sujet] ?? LuZap
                return (
                  <Icone
                    size={14}
                    className={`shrink-0 ${
                      e.valeur > 0 ? 'text-accent-vif' : 'text-texte-faible'
                    }`}
                  />
                )
              })()}
              <span className="min-w-0 flex-1 truncate text-micro text-texte">
                {NOMS[e.sujet] ?? e.sujet}
                {/* Le point marque la transition : allume ou eteint. */}
                <LuCircleDot
                  size={9}
                  className={`mx-1.5 inline shrink-0 align-[-0.05em] ${
                    e.valeur > 0 ? 'text-accent-vif' : 'text-texte-faible/50'
                  }`}
                />
                <span className="text-texte-doux">
                  {e.valeur > 0 ? 'activé' : 'arrêté'}
                </span>
              </span>
              <span
                className={`shrink-0 text-nano font-medium ${
                  ORIGINES[e.source]?.classe ?? 'text-texte-faible'
                }`}
              >
                {ORIGINES[e.source]?.libelle ?? e.source}
              </span>
            </>
          )}

          <span className="w-20 shrink-0 text-right text-nano tabular-nums text-texte-faible">
            {depuis(e.ts)}
          </span>
        </li>
      ))}
    </ul>
  )
}
