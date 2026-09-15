/** Le logo de Botanik : une graine de lentille, sa nervure evidee.
 *
 *  Silhouette et nervure sont reunies en un seul trace avec
 *  `fill-rule="evenodd"` : la nervure devient un vide et laisse passer le
 *  fond, quel qu'il soit. Le degrade porte une contre-rotation pour que
 *  la lumiere reste en haut a gauche alors que la graine, elle, penche. */
export default function Logo({ taille = 28 }: { taille?: number }) {
  const id = 'logo-botanik'
  return (
    <svg width={taille} height={taille} viewBox="0 0 32 32" aria-hidden>
      <defs>
        <linearGradient
          id={id} x1="5" y1="5" x2="27" y2="27"
          gradientUnits="userSpaceOnUse"
          gradientTransform="rotate(-30 16 16)"
        >
          <stop stopColor="#a3e635" />
          <stop offset=".55" stopColor="#22c55e" />
          <stop offset="1" stopColor="#15803d" />
        </linearGradient>
      </defs>
      <g transform="rotate(30 16 16)">
        <path
          fill={`url(#${id})`}
          fillRule="evenodd"
          d="M16 5.5c9.5 6.6 9.5 15.8 0 22.4-9.5-6.6-9.5-15.8 0-22.4Z
             M16 27.6c-5-5.8 5-10.8 0-21.9-1.3 11.1-8.6 16 0 21.9Z"
        />
      </g>
    </svg>
  )
}
