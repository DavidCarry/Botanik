import { LuCircleCheck, LuTriangleAlert, LuUserRound } from 'react-icons/lu'
import type { Alerte } from '../api'
import { depuis } from '../format'

/** Les problemes en cours.
 *
 *  Une alerte reste affichee pendant que la serre y remedie : la pompe
 *  tourne, mais le sol est encore trop sec. Montrer le probleme ET sa
 *  prise en charge vaut mieux que de le faire disparaitre des qu'une
 *  action demarre -- sinon on ne verrait jamais rien.
 */
export default function Alertes({ liste }: { liste: Alerte[] }) {
  if (liste.length === 0) {
    return (
      <p className="flex items-center justify-center gap-2 py-6 text-micro text-texte-doux">
        <LuCircleCheck size={15} className="text-bon" />
        Aucun problème en cours
      </p>
    )
  }

  return (
    <ul className="divide-y divide-bordure">
      {liste.map((a) => (
        <li key={`${a.grandeur}-${a.cote}`} className="flex items-center gap-3 py-2.5">
          <LuTriangleAlert
            size={15}
            className={`shrink-0 ${a.humaine ? 'text-critique' : 'text-attention'}`}
          />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-menu font-medium text-texte">
              {a.libelle}
            </span>
            <span className="flex items-center gap-1.5 text-micro text-texte-faible">
              {a.humaine ? (
                <>
                  <LuUserRound size={11} className="shrink-0" />
                  demande une intervention
                </>
              ) : (
                'la serre y remédie'
              )}
            </span>
          </span>
          <span className="shrink-0 whitespace-nowrap text-micro tabular-nums text-texte-faible">
            {depuis(a.depuis)}
          </span>
        </li>
      ))}
    </ul>
  )
}
