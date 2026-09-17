type Props = {
  libelle: string
  valeur: string
  unite?: string
  /** part remplie, 0 a 1 */
  niveau: number
  /** bornes de la plage favorable, 0 a 1 */
  ideal: { bas: number; haut: number }
  dansLaPlage: boolean
  /** plus aucune mesure recue : la valeur affichee est figee */
  muet?: boolean
  /** aucune sonde derriere : la valeur est inventee, et on le dit */
  simule?: boolean
  /** diametre et coin superieur gauche, en % du carre de reference */
  taille: number
  x: number
  y: number
  /** decale les vagues pour que les billes ne battent pas a l'unisson */
  retard: number
}

/** Une courbe sinusoidale assez large pour defiler sans montrer de
 *  raccord : deux periodes completes, on n'en translate qu'une. */
function vague(amplitude: number): string {
  const l = 200
  let d = `M 0 ${amplitude}`
  for (let x = 0; x <= l; x += 5) {
    d += ` L ${x} ${amplitude + Math.sin((x / 50) * Math.PI * 2) * amplitude}`
  }
  return `${d} L ${l} 130 L 0 130 Z`
}

const VAGUE_HAUTE = vague(2.6)
const VAGUE_BASSE = vague(1.8)

export default function SphereLiquide({
  libelle, valeur, unite, niveau, ideal, dansLaPlage, muet, simule,
  taille, x, y, retard,
}: Props) {
  const id = libelle.replace(/[^a-z]/gi, '') || 'x'
  const rempli = Math.max(0, Math.min(1, niveau))

  // Repere SVG en 0-100 : le liquide monte donc de 100 (vide) vers 0.
  const yLiquide = 100 - rempli * 100
  const yIdealHaut = 100 - ideal.haut * 100
  const yIdealBas = 100 - ideal.bas * 100

  // Tout passe par des attributs SVG et par SMIL, jamais par CSS : a
  // l'interieur d'un clipPath, les animations CSS ne sont pas prises en
  // compte -- le decoupage resterait fige, ou ne s'appliquerait pas du
  // tout. SMIL, lui, y fonctionne, et les deux vagues restent en phase.
  const glisse = `translate(0 ${yLiquide})`

  /** La houle, en animation SVG native.
   *
   *  Un `animateTransform` REMPLACE le transform de l'element, il ne s'y
   *  ajoute pas. D'ou le parametre `y` : dans le clipPath, ou aucun groupe
   *  ne peut porter le niveau, l'animation doit le porter elle-meme ; dans
   *  le liquide visible, le groupe s'en charge et y vaut 0.
   *  `begin` negatif decale la phase sans attendre. */
  const houle = (duree: number, debut: number, y = yLiquide) => (
    <animateTransform
      attributeName="transform" type="translate"
      from={`0 ${y}`} to={`-50 ${y}`}
      dur={`${duree}s`} begin={`${debut}s`} repeatCount="indefinite"
    />
  )
  const corps = valeur.length > 4 ? 15 : valeur.length > 3 ? 18 : 21

  // Le texte est ecrit deux fois : une version claire, puis une version
  // sombre decoupee a la forme exacte du liquide. Ce qui depasse reste
  // clair, ce qui plonge passe en sombre -- la coupure tombe pile sur la
  // ligne d'eau, meme au milieu d'un chiffre.
  const texte = (couleurLibelle: string, couleurValeur: string) => (
    <>
      <text
        x="50" y={44} textAnchor="middle" fill={couleurLibelle}
        fontSize="6.4" fontWeight="500" letterSpacing="0.5"
        style={{ textTransform: 'uppercase' }}
      >
        {libelle.toUpperCase()}
      </text>
      <text x="50" y={64} textAnchor="middle" fill={couleurValeur}
            fontSize={corps} fontWeight="600" letterSpacing="-0.5">
        {valeur}
        {unite && (
          <tspan fontSize={corps * 0.42} fontWeight="500" dx="1">{unite}</tspan>
        )}
      </text>

      {/* Une valeur sans sonde derriere le dit, en toutes lettres et
          dans la bille. Le materiel arrive par morceaux : pendant tout
          ce temps l'ecran melange des mesures et des inventions, et
          rien ne doit laisser croire l'une pour l'autre. */}
      {simule && (
        <text
          x="50" y={78} textAnchor="middle" fill={couleurLibelle}
          fontSize="4.6" fontWeight="500" letterSpacing="0.9" opacity="0.75"
        >
          SIMULÉ
        </text>
      )}
    </>
  )

  return (
    <div
      // Une bille muette s'eteint plutot que de disparaitre : la derniere
      // valeur connue reste lisible, mais on voit qu'elle n'est plus
      // rafraichie. Le titre dit pourquoi a qui s'y attarde.
      className={`sphere absolute overflow-hidden${muet ? ' opacity-40' : ''}`}
      title={
        muet ? `${libelle} : aucune mesure depuis plus d’une minute`
          : simule ? `${libelle} : valeur simulée, aucune sonde n’est câblée`
            : undefined
      }
      style={{
        width: `${taille}%`, height: `${taille}%`,
        left: `${x}%`, top: `${y}%`,
      }}
    >
      <svg viewBox="0 0 100 100" className="size-full">
        <defs>
          <clipPath id={`bille-${id}`}>
            <circle cx="50" cy="50" r="50" />
          </clipPath>

          {/* Meme geometrie et memes animations que le liquide visible :
              les deux restent en phase, donc la decoupe epouse la vague. */}
          <clipPath id={`eau-${id}`}>
            <path d={VAGUE_HAUTE} transform={glisse}>
              {houle(4.2, retard * 1.7)}
            </path>
          </clipPath>

          <linearGradient id={`liquide-${id}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent-vif)" stopOpacity="0.75" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.4" />
          </linearGradient>
        </defs>

        <g clipPath={`url(#bille-${id})`}>
          {/* Plage favorable : on lit d'un coup si le niveau y tombe. */}
          <rect
            x="0" y={yIdealHaut} width="100"
            height={Math.max(yIdealBas - yIdealHaut, 0.8)}
            fill={dansLaPlage ? 'var(--accent)' : 'var(--attention)'}
            opacity="0.13"
          />
          <line x1="0" x2="100" y1={yIdealHaut} y2={yIdealHaut}
                stroke="var(--texte)" strokeOpacity="0.18" strokeWidth="0.5" />
          <line x1="0" x2="100" y1={yIdealBas} y2={yIdealBas}
                stroke="var(--texte)" strokeOpacity="0.18" strokeWidth="0.5" />

          {/* Deux vagues de periodes differentes : leur dephasage continu
              evite le battement mecanique d'une seule. */}
          <g transform={glisse} style={{ transition: 'transform 900ms var(--ease-doux)' }}>
            <path d={VAGUE_BASSE} fill={`url(#liquide-${id})`} opacity="0.5">
              {houle(6.7, retard, 0)}
            </path>
            <path d={VAGUE_HAUTE} fill={`url(#liquide-${id})`}>
              {houle(4.2, retard * 1.7, 0)}
            </path>
          </g>

          {texte('var(--texte-doux)', 'var(--texte)')}
          <g clipPath={`url(#eau-${id})`}>
            {texte('rgba(4,20,12,0.62)', '#041a0e')}
          </g>
        </g>
      </svg>
    </div>
  )
}
