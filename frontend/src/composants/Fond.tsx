/** Fond : des lueurs largement floutees qui derivent et se recouvrent.
 *
 *  Chaque lueur est portee par deux pistes imbriquees, l'une horizontale
 *  et l'autre verticale. Leurs periodes, leurs amplitudes, leur sens et
 *  leur point de depart sont TIRES AU SORT au chargement : aucun trajet
 *  n'est ecrit nulle part, chacun emerge de la combinaison des deux.
 *
 *  Comme les periodes sont des nombres reels, elles n'ont pratiquement
 *  jamais de rapport simple entre elles : la trajectoire ne se referme
 *  pas avant des dizaines de minutes.
 */

type Halo = {
  teinte: string
  /** position de repos et taille */
  classes: string
}

const HALOS: Halo[] = [
  { teinte: 'var(--halo-1)', classes: 'left-[2%] top-[4%] h-[34vh] w-[24vw]' },
  { teinte: 'var(--halo-2)', classes: 'left-[32%] top-[-2%] h-[29vh] w-[21vw]' },
  { teinte: 'var(--halo-3)', classes: 'right-[4%] top-[2%] h-[32vh] w-[23vw]' },
  { teinte: 'var(--halo-5)', classes: 'left-[16%] top-[34%] h-[28vh] w-[20vw]' },
  { teinte: 'var(--halo-6)', classes: 'left-[54%] top-[28%] h-[31vh] w-[22vw]' },
  { teinte: 'var(--halo-4)', classes: 'left-[4%] bottom-[2%] h-[33vh] w-[24vw]' },
  { teinte: 'var(--halo-8)', classes: 'left-[36%] bottom-[-2%] h-[28vh] w-[21vw]' },
  { teinte: 'var(--halo-7)', classes: 'right-[2%] bottom-[4%] h-[33vh] w-[23vw]' },
]

const entre = (min: number, max: number) => min + Math.random() * (max - min)
const signe = () => (Math.random() < 0.5 ? -1 : 1)

/** Tire une fois, au chargement du module, pour que le rendu des
 *  composants reste pur. Chaque visite compose un tableau different. */
const TRAJETS = HALOS.map(() => ({
  // periodes, en secondes
  px: entre(19, 47),
  py: entre(19, 47),
  pr: entre(15, 33),
  // amplitudes, avec un sens tire au hasard
  ax: signe() * entre(9, 19),
  ay: signe() * entre(7, 14),
  // respiration
  bas: entre(0.78, 0.92),
  haut: entre(1.14, 1.32),
  // point de depart dans le cycle
  dx: -Math.random() * 90,
  dy: -Math.random() * 90,
  dr: -Math.random() * 60,
}))

export default function Fond() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-page">
      <div className="halos">
        {HALOS.map((h, i) => {
          const t = TRAJETS[i]
          return (
            <span
              key={i}
              className="piste-x"
              style={{
                '--amplitude': `${t.ax.toFixed(2)}vw`,
                animationDuration: `${t.px.toFixed(2)}s`,
                animationDelay: `${t.dx.toFixed(2)}s`,
              } as React.CSSProperties}
            >
              <span
                className="piste-y"
                style={{
                  '--amplitude': `${t.ay.toFixed(2)}vh`,
                  animationDuration: `${t.py.toFixed(2)}s`,
                  animationDelay: `${t.dy.toFixed(2)}s`,
                } as React.CSSProperties}
              >
                <span
                  className={`halo ${h.classes}`}
                  style={{
                    background: h.teinte,
                    '--souffle-bas': t.bas.toFixed(3),
                    '--souffle-haut': t.haut.toFixed(3),
                    animationDuration: `${t.pr.toFixed(2)}s`,
                    animationDelay: `${t.dr.toFixed(2)}s`,
                  } as React.CSSProperties}
                />
              </span>
            </span>
          )
        })}
      </div>
      <span className="vignette" />
      <span className="grain" />
    </div>
  )
}
