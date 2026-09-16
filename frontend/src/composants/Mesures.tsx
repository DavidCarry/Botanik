import { formaterValeur } from '../format'
import { LIBELLE_BILLE } from '../libelles'
import { useMesures } from '../useMesures'
import { plage, useModele } from '../useModele'
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
  const modele = useModele()

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
          // La plage vient du reseau quand il en a appris une ; sinon du
          // registre. Une seule bulle est concernee aujourd'hui, celle
          // que le modele pilote.
          const bornes = c ? plage(c, modele) : null
          const dedans = Boolean(c && m && bornes
            && m.valeur >= bornes.min && m.valeur <= bornes.max)
          const muet = Boolean(c && muets.has(c.id))

          return (
            <SphereLiquide
              key={c?.id ?? i}
              libelle={c ? (LIBELLE_BILLE[c.id] ?? c.libelle) : '—'}
              valeur={m ? formaterValeur(m.valeur, c!.unite) : '—'}
              unite={m ? c!.unite : undefined}
              niveau={niveau}
              ideal={c && bornes
                ? { bas: part(bornes.min, c.echelle.min, c.echelle.max),
                    haut: part(bornes.max, c.echelle.min, c.echelle.max) }
                : { bas: 0, haut: 0 }}
              dansLaPlage={dedans}
              muet={muet}
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
