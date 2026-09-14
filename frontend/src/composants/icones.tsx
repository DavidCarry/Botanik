/** Icones inline : pas de dependance, et elles heritent de la couleur du texte. */

const base = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

export function IconeTemperature() {
  return (
    <svg {...base}>
      <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" />
    </svg>
  )
}

export function IconeHumidite() {
  return (
    <svg {...base}>
      <path d="M12 2.7s6 5.4 6 9.8a6 6 0 0 1-12 0c0-4.4 6-9.8 6-9.8z" />
    </svg>
  )
}

export function IconeLuminosite() {
  return (
    <svg {...base}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  )
}

export function IconeEau() {
  return (
    <svg {...base}>
      <path d="M5 8h14v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V8z" />
      <path d="M4 8h16M8 8V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v3" />
      <path d="M7 14h10" />
    </svg>
  )
}
