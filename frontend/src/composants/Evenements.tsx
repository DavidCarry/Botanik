import { LuCircleDot, LuDroplet, LuFan, LuShieldAlert, LuSun, LuZap } from 'react-icons/lu'
import type { IconType } from 'react-icons'
import type { Evenement } from '../api'
import { depuis } from '../format'
import { useEvenements } from '../useEvenements'

const ICONES: Record<string, IconType> = {
  pompe: LuDroplet,
  lumiere: LuSun,
  ventilation: LuFan,
}

const NOMS: Record<string, string> = {
  pompe: 'Arrosage',
  lumiere: 'Éclairage',
  ventilation: 'Ventilation',
}

/** Qui a decide. La distinction est le seul moyen de relire apres coup
 *  ce qu'a fait le reseau, et de le separer de ce qu'on a fait soi-meme. */
const ORIGINES: Record<Evenement['source'], { libelle: string; classe: string }> = {
  manuel: { libelle: 'manuel', classe: 'text-texte-faible' },
  ia: { libelle: 'IA', classe: 'text-accent-vif' },
  securite: { libelle: 'sécurité', classe: 'text-attention' },
}

export default function Evenements() {
  const liste = useEvenements()

  if (liste === null) {
    return <p className="text-micro text-texte-faible">Lecture du journal…</p>
  }
  if (liste.length === 0) {
    return (
      <p className="grid h-full place-items-center text-micro text-texte-faible">
        Aucune commande enregistrée
      </p>
    )
  }

  return (
    <ul className="h-full space-y-px overflow-y-auto pr-1">
      {liste.map((e, i) => {
        const Icone = ICONES[e.actionneur] ?? LuZap
        const allume = e.valeur > 0
        const origine = ORIGINES[e.source]
        return (
          <li
            key={`${e.ts}-${e.actionneur}-${i}`}
            className="flex items-center gap-2.5 rounded-carte px-1.5 py-1.5 transition-colors hover:bg-texte/[0.03]"
          >
            {e.source === 'securite' ? (
              <LuShieldAlert size={14} className="shrink-0 text-attention" />
            ) : (
              <Icone
                size={14}
                className={`shrink-0 ${allume ? 'text-accent-vif' : 'text-texte-faible'}`}
              />
            )}

            <span className="min-w-0 flex-1 truncate text-micro text-texte">
              {NOMS[e.actionneur] ?? e.actionneur}
              {/* Le point marque la transition : allume ou eteint. */}
              <LuCircleDot
                size={9}
                className={`mx-1.5 inline shrink-0 align-[-0.05em] ${
                  allume ? 'text-accent' : 'text-texte-faible/50'
                }`}
              />
              <span className="text-texte-doux">{allume ? 'activé' : 'arrêté'}</span>
            </span>

            <span className={`shrink-0 text-[0.6rem] font-medium ${origine.classe}`}>
              {origine.libelle}
            </span>
            <span className="w-20 shrink-0 text-right text-[0.6rem] tabular-nums text-texte-faible">
              {depuis(e.ts)}
            </span>
          </li>
        )
      })}
    </ul>
  )
}
