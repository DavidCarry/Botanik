import { formaterValeur } from '../format'
import { LIBELLE_BILLE } from '../libelles'
import { useMesures } from '../useMesures'
import SphereLiquide from './SphereLiquide'

/** Quatre billes en contact, sans le moindre recouvrement.
 *
 *  Construction : Temperature et Lumiere sont d'abord rendues tangentes
 *  l'une a l'autre ; Humidite et Eau sont ensuite placees de part et
 *  d'autre de cette ligne, chacune tangente AUX DEUX -- ce qui determine
 *  leur position de facon unique. Il en resulte cinq tangences et aucun
 *  interstice central. Valeurs non arrondies : l'arrondi decollerait les
 *  bords. */
const GRAPPE = [
  { taille: 56.1, cx: 29.06, cy: 32.00, retard: 0 },
  { taille: 42.1, cx: 77.96, cy: 27.74, retard: -1.4 },
  { taille: 40.1, cx: 63.06, cy: 66.00, retard: -2.6 },
  { taille: 36.1, cx: 26.95, cy: 78.04, retard: -3.3 },
]

const part = (v: number, min: number, max: number) =>
  Math.max(0, Math.min(1, (v - min) / (max - min)))

export default function Mesures() {
  const { capteurs, muets } = useMesures()

  const cases = capteurs?.length ? capteurs.slice(0, 4) : [null, null, null, null]

  return (
    <div
      className="flex h-full min-h-0 items-center justify-center"
      style={{ containerType: 'size' }}
    >
      {/* Un carre qui tient dans un rectangle quelconque : on prend la
          plus petite des deux dimensions du parent. */}
      <div className="relative" style={{ width: 'min(100%, 100cqh)', aspectRatio: '1' }}>
        {cases.map((c, i) => {
          const { taille, cx, cy, retard } = GRAPPE[i]
          const m = c?.mesure
          const niveau = c && m ? part(m.valeur, c.echelle.min, c.echelle.max) : 0
          // La plage vient de la REGLE posee par l'utilisateur, resolue
          // par le serveur. Aucune regle, aucune plage : la bulle ne
          // trace alors rien, plutot que d'afficher une consigne que
          // personne n'a donnee.
          //
          // Une borne peut manquer -- « au-dessus de 50 » est une
          // consigne complete -- et ce cote vaut alors l'infini.
          const bornes = c?.plage ?? null
          const dedans = !bornes || !m ? true : (
            (bornes.bas == null || m.valeur >= bornes.bas)
            && (bornes.haut == null || m.valeur <= bornes.haut)
          )
          const muet = Boolean(c && muets.has(c.id))

          return (
            <SphereLiquide
              key={c?.id ?? i}
              libelle={c ? (LIBELLE_BILLE[c.id] ?? c.libelle) : '—'}
              valeur={m ? formaterValeur(m.valeur, c!.unite) : '—'}
              unite={m ? c!.unite : undefined}
              niveau={niveau}
              ideal={c && bornes
                ? {
                    bas: bornes.bas == null ? 0
                      : part(bornes.bas, c.echelle.min, c.echelle.max),
                    haut: bornes.haut == null ? 1
                      : part(bornes.haut, c.echelle.min, c.echelle.max),
                  }
                : null}
              dansLaPlage={dedans}
              muet={muet}
              simule={Boolean(c?.simule)}
              taille={taille}
              x={cx - taille / 2}
              y={cy - taille / 2}
              retard={retard}
            />
          )
        })}
      </div>
    </div>
  )
}
