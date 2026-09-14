type Props = {
  valeur: number
  min: number
  max: number
  idealMin: number
  idealMax: number
}

const pourcent = (v: number, min: number, max: number) =>
  Math.min(100, Math.max(0, ((v - min) / (max - min)) * 100))

/** Situe la valeur dans son intervalle : la zone ideale est marquee sur la
 *  piste, un curseur indique ou l'on se trouve. Bien plus parlant qu'un
 *  nombre seul -- on voit d'un coup d'oeil si on derive. */
export default function Jauge({ valeur, min, max, idealMin, idealMax }: Props) {
  const debut = pourcent(idealMin, min, max)
  const fin = pourcent(idealMax, min, max)

  return (
    <div className="relative h-1.5 w-full rounded-full bg-ink/8 dark:bg-ink/12">
      <div
        className="absolute h-full rounded-full bg-ink/15 dark:bg-ink/20"
        style={{ left: `${debut}%`, width: `${fin - debut}%` }}
      />
      <div
        className="absolute top-1/2 h-3 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink"
        style={{ left: `${pourcent(valeur, min, max)}%` }}
      />
    </div>
  )
}
