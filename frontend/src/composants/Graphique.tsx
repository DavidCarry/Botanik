import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { Point } from '../api'

type Props = {
  points: Point[]
  unite: string
  ideal: { min: number; max: number }
}

// La legende des valeurs occupe la gauche ; le trace commence apres.
const MARGE = { haut: 12, bas: 20, gauche: 40, droite: 8 }
const DUREE = 620

/** Lissage Catmull-Rom converti en Beziers cubiques.
 *  Une polyligne brute fait un angle a chaque mesure ; la tension
 *  arrondit les sommets sans jamais s'ecarter des points. */
function lisser(pts: [number, number][]): string {
  if (pts.length === 0) return ''
  if (pts.length === 1) return `M ${pts[0][0]} ${pts[0][1]}`

  const T = 0.18
  let d = `M ${pts[0][0]} ${pts[0][1]}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[i + 2] ?? p2
    d += ` C ${p1[0] + (p2[0] - p0[0]) * T} ${p1[1] + (p2[1] - p0[1]) * T},`
    d += ` ${p2[0] - (p3[0] - p1[0]) * T} ${p2[1] - (p3[1] - p1[1]) * T},`
    d += ` ${p2[0]} ${p2[1]}`
  }
  return d
}

/** Ramene une serie a un nombre de points donne, par interpolation
 *  lineaire. Sans cela, passer de 1 jour (17 points) a 1 semaine (84)
 *  n'offrirait aucune correspondance a animer. */
function reechantillonner(valeurs: number[], n: number): number[] {
  if (valeurs.length === 0) return Array(n).fill(0)
  if (valeurs.length === 1) return Array(n).fill(valeurs[0])
  return Array.from({ length: n }, (_, i) => {
    const t = (i / Math.max(n - 1, 1)) * (valeurs.length - 1)
    const a = Math.floor(t)
    const b = Math.min(a + 1, valeurs.length - 1)
    return valeurs[a] + (valeurs[b] - valeurs[a]) * (t - a)
  })
}

const adouci = (t: number) => 1 - Math.pow(1 - t, 3)

type Geometrie = {
  ligne: string
  aire: string
  coords: [number, number][]
  bandeY: number
  bandeH: number
  bas: number
  haut: number
  yIdealMin: number
  yIdealMax: number
}

function geometrie(
  valeurs: number[], l: number, h: number, ideal: { min: number; max: number },
): Geometrie {
  const x0 = MARGE.gauche
  const x1 = l - MARGE.droite
  const y0 = MARGE.haut
  const y1 = h - MARGE.bas

  // L'echelle englobe la plage ideale : sans cela la bande sortirait du
  // cadre des que les mesures s'en approchent.
  let bas = Math.min(...valeurs, ideal.min)
  let haut = Math.max(...valeurs, ideal.max)
  const marge = (haut - bas) * 0.12 || 1
  bas -= marge
  haut += marge

  const px = (i: number) =>
    valeurs.length === 1 ? (x0 + x1) / 2 : x0 + (i / (valeurs.length - 1)) * (x1 - x0)
  const py = (v: number) => y1 - ((v - bas) / (haut - bas)) * (y1 - y0)

  const coords = valeurs.map((v, i) => [px(i), py(v)] as [number, number])
  const ligne = lisser(coords)
  const fin = coords[coords.length - 1]
  const aire = `${ligne} L ${fin[0]} ${y1} L ${coords[0][0]} ${y1} Z`

  const yIdealMax = py(ideal.max)
  const yIdealMin = py(ideal.min)

  return {
    ligne, aire, coords,
    bandeY: yIdealMax, bandeH: yIdealMin - yIdealMax,
    bas, haut, yIdealMin, yIdealMax,
  }
}

const heure = (iso: string) =>
  new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })

const jour = (iso: string) =>
  new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })

export default function Graphique({ points, unite, ideal }: Props) {
  const boite = useRef<HTMLDivElement>(null)
  const [taille, setTaille] = useState({ l: 0, h: 0 })
  const [survol, setSurvol] = useState<number | null>(null)

  const rLigne = useRef<SVGPathElement>(null)
  const rAire = useRef<SVGPathElement>(null)
  const rBande = useRef<SVGRectElement>(null)
  const rSeuilHaut = useRef<SVGLineElement>(null)
  const rSeuilBas = useRef<SVGLineElement>(null)
  const rPoint = useRef<SVGCircleElement>(null)
  const rLegende = useRef<HTMLDivElement>(null)

  /** Derniere serie reellement dessinee : point de depart de la prochaine
   *  interpolation. Une ref et non un etat -- l'animation ne doit
   *  declencher aucun rendu React. */
  const affichees = useRef<number[]>([])

  // Le SVG est dessine en pixels reels : un viewBox etire deformerait les
  // disques et l'epaisseur des traits.
  useLayoutEffect(() => {
    const el = boite.current
    if (!el) return
    const obs = new ResizeObserver(([e]) => {
      const r = e.contentRect
      setTaille({ l: Math.round(r.width), h: Math.round(r.height) })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const { l, h } = taille
  const pret = l > 0 && h > 0 && points.length > 0

  // On interpole les VALEURS, pas le chemin : deformer le trace point par
  // point donne le glissement continu d'une appli boursiere, la ou un
  // fondu se contenterait de remplacer une image par une autre.
  useEffect(() => {
    if (!pret) return

    const cible = points.map((p) => p.valeur)
    const premier = affichees.current.length === 0
    const depart = reechantillonner(affichees.current, cible.length)

    const peindre = (valeurs: number[]) => {
      const g = geometrie(valeurs, l, h, ideal)
      rLigne.current?.setAttribute('d', g.ligne)
      rAire.current?.setAttribute('d', g.aire)
      rBande.current?.setAttribute('y', String(g.bandeY))
      rBande.current?.setAttribute('height', String(Math.max(g.bandeH, 1)))
      rSeuilHaut.current?.setAttribute('y1', String(g.bandeY))
      rSeuilHaut.current?.setAttribute('y2', String(g.bandeY))
      rSeuilBas.current?.setAttribute('y1', String(g.bandeY + g.bandeH))
      rSeuilBas.current?.setAttribute('y2', String(g.bandeY + g.bandeH))

      const fin = g.coords[g.coords.length - 1]
      rPoint.current?.setAttribute('cx', String(fin[0]))
      rPoint.current?.setAttribute('cy', String(fin[1]))

      // Les reperes suivent l'echelle, sinon ils sauteraient a la fin.
      const leg = rLegende.current
      if (leg) {
        const e = Array.from(leg.children) as HTMLElement[]
        e[0].textContent = String(Math.round(g.haut * 10) / 10)
        e[1].style.top = `${g.yIdealMax}px`
        e[2].style.top = `${g.yIdealMin}px`
        e[3].textContent = String(Math.round(g.bas * 10) / 10)
      }
      affichees.current = valeurs
    }

    if (premier) {
      peindre(cible)
      return
    }

    let raf = 0
    const t0 = performance.now()
    const pas = () => {
      const t = Math.min(1, (performance.now() - t0) / DUREE)
      const e = adouci(t)
      peindre(cible.map((v, i) => depart[i] + (v - depart[i]) * e))
      if (t < 1) raf = requestAnimationFrame(pas)
    }
    raf = requestAnimationFrame(pas)
    return () => cancelAnimationFrame(raf)
  }, [points, l, h, ideal, pret])

  // Geometrie de reference, pour le rendu initial et le reperage du
  // survol. Elle part des points cibles : l'animation, elle, ecrit
  // directement dans le DOM et n'a pas besoin de repasser par React.
  const g = pret ? geometrie(points.map((p) => p.valeur), l, h, ideal) : null

  const iSurvol = survol !== null && g
    ? Math.min(points.length - 1, Math.max(0, Math.round(
        ((survol - MARGE.gauche) / (l - MARGE.gauche - MARGE.droite)) * (points.length - 1),
      )))
    : null

  return (
    <div ref={boite} className="relative h-full w-full">
      {!pret && (
        <p className="grid h-full place-items-center text-micro text-texte-faible">
          Pas encore de mesure sur cette période
        </p>
      )}

      {pret && g && (
        <>
          <svg
            width={l}
            height={h}
            className="block"
            onPointerMove={(e) =>
              setSurvol(e.clientX - e.currentTarget.getBoundingClientRect().left)
            }
            onPointerLeave={() => setSurvol(null)}
          >
            <defs>
              {/* Degrade cale sur la boite du trace : son sommet suit donc
                  la courbe, et non le haut du cadre. Il s'eteint vite pour
                  concentrer la matiere sous la ligne. */}
              <linearGradient id="sous-courbe" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--accent-vif)" stopOpacity="0.62" />
                <stop offset="9%" stopColor="var(--accent-vif)" stopOpacity="0.30" />
                <stop offset="22%" stopColor="var(--accent-vif)" stopOpacity="0.10" />
                <stop offset="40%" stopColor="var(--accent-vif)" stopOpacity="0.02" />
                <stop offset="58%" stopColor="var(--accent-vif)" stopOpacity="0" />
              </linearGradient>
              <filter id="neon" x="-20%" y="-40%" width="140%" height="180%">
                <feGaussianBlur stdDeviation="3.5" result="flou" />
                <feMerge>
                  <feMergeNode in="flou" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Plage favorable : deux seuils seulement. La bande pleine
                colorait tout l'arriere-plan et concurrencait la courbe. */}
            <rect
              ref={rBande}
              x={MARGE.gauche} y={g.bandeY}
              width={l - MARGE.gauche - MARGE.droite}
              height={Math.max(g.bandeH, 1)}
              fill="none"
            />
            <line ref={rSeuilHaut}
              x1={MARGE.gauche} x2={l - MARGE.droite} y1={g.bandeY} y2={g.bandeY}
              stroke="var(--accent)" strokeOpacity="0.35" strokeWidth="1" strokeDasharray="3 4" />
            <line ref={rSeuilBas}
              x1={MARGE.gauche} x2={l - MARGE.droite}
              y1={g.bandeY + g.bandeH} y2={g.bandeY + g.bandeH}
              stroke="var(--accent)" strokeOpacity="0.35" strokeWidth="1" strokeDasharray="3 4" />

            <path ref={rAire} d={g.aire} fill="url(#sous-courbe)" />
            <path
              ref={rLigne} d={g.ligne} fill="none"
              stroke="var(--accent-vif)" strokeWidth="2"
              strokeLinecap="round" strokeLinejoin="round" filter="url(#neon)"
            />

            {iSurvol !== null && g.coords[iSurvol] && (
              <>
                <line
                  x1={g.coords[iSurvol][0]} x2={g.coords[iSurvol][0]}
                  y1={MARGE.haut} y2={h - MARGE.bas}
                  stroke="var(--texte)" strokeOpacity="0.22" strokeWidth="1"
                />
                <circle
                  cx={g.coords[iSurvol][0]} cy={g.coords[iSurvol][1]} r="5"
                  fill="var(--accent-vif)" stroke="var(--page)" strokeWidth="2"
                />
              </>
            )}

            <circle
              ref={rPoint}
              cx={g.coords[g.coords.length - 1][0]}
              cy={g.coords[g.coords.length - 1][1]}
              r="4.5"
              fill="var(--accent-vif)" stroke="var(--page)" strokeWidth="2"
              filter="url(#neon)"
              opacity={iSurvol === null ? 1 : 0}
            />
          </svg>

          {/* Reperes de valeur. Quatre suffisent : les deux bornes de la
              plage favorable -- l'information utile -- et les extremes de
              l'echelle, qui ne servent qu'a cadrer. */}
          <div ref={rLegende}
               className="pointer-events-none absolute inset-y-0 left-0 w-9 text-right text-[0.6rem] tabular-nums">
            <span className="absolute right-0 -translate-y-1/2 text-texte-faible"
                  style={{ top: MARGE.haut }}>
              {Math.round(g.haut * 10) / 10}
            </span>
            <span className="absolute right-0 -translate-y-1/2 font-medium text-accent"
                  style={{ top: g.yIdealMax }}>
              {ideal.max}
            </span>
            <span className="absolute right-0 -translate-y-1/2 font-medium text-accent"
                  style={{ top: g.yIdealMin }}>
              {ideal.min}
            </span>
            <span className="absolute right-0 -translate-y-1/2 text-texte-faible"
                  style={{ top: h - MARGE.bas }}>
              {Math.round(g.bas * 10) / 10}
            </span>
          </div>

          <div className="pointer-events-none absolute bottom-0 left-10 right-2 flex justify-between text-[0.6rem] text-texte-faible">
            <span>{points.length > 12 ? jour(points[0].ts) : heure(points[0].ts)}</span>
            <span>{heure(points[points.length - 1].ts)}</span>
          </div>

          {iSurvol !== null && g.coords[iSurvol] && (
            <div
              className="pointer-events-none absolute top-0 -translate-x-1/2 rounded-lg border border-bordure bg-surface-creuse px-2 py-1 backdrop-blur-md"
              style={{ left: Math.min(Math.max(g.coords[iSurvol][0], 46), l - 46) }}
            >
              <p className="whitespace-nowrap text-center">
                <span className="text-menu font-semibold text-texte">
                  {points[iSurvol].valeur}
                </span>
                <span className="ml-0.5 text-[0.6rem] text-texte-doux">{unite}</span>
              </p>
              <p className="text-center text-[0.6rem] text-texte-faible">
                {heure(points[iSurvol].ts)}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
