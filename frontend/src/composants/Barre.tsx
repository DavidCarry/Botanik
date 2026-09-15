type Props = {
  part: number
  /** au-dela, la barre passe en alerte */
  seuil?: number
}

/** Jauge horizontale. Sert aux ressources de la machine ; la couleur
 *  double l'information portee par la longueur, elle ne la remplace pas. */
export default function Barre({ part, seuil = 85 }: Props) {
  const p = Math.max(0, Math.min(100, part))
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-pilule bg-texte/10">
      <div
        className="h-full rounded-pilule transition-[width] duration-700 ease-out"
        style={{
          width: `${p}%`,
          background: p >= seuil ? 'var(--attention)' : 'var(--accent)',
        }}
      />
    </div>
  )
}
