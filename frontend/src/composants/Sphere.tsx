type Props = {
  libelle: string
  valeur: string
  unite?: string
  /** part du carre de reference, en % : diametre et coin superieur gauche */
  taille: number
  x: number
  y: number
}

/** Une mesure dans une bille de verre.
 *
 *  `container-type` est pose sur la bille elle-meme : les unites `cqw`
 *  se rapportent alors a SON diametre, pas a celui du conteneur commun.
 *  Sans cela, toutes les billes heriteraient de la meme taille de texte
 *  et les petites deborderaient.
 */
export default function Sphere({ libelle, valeur, unite, taille, x, y }: Props) {
  // Une valeur longue doit tenir dans la meme largeur qu'une valeur courte.
  const serrage = valeur.length > 4 ? 0.74 : valeur.length > 3 ? 0.87 : 1

  return (
    <div
      className="sphere absolute grid place-items-center"
      style={{
        width: `${taille}%`,
        height: `${taille}%`,
        left: `${x}%`,
        top: `${y}%`,
        containerType: 'inline-size',
      }}
    >
      <div className="w-full px-[9%] text-center leading-none">
        <p
          className="truncate font-medium uppercase tracking-[0.08em] text-texte-faible"
          style={{ fontSize: 'clamp(0.47rem, 10cqw, 0.7rem)' }}
        >
          {libelle}
        </p>
        <p className="mt-[0.4em] flex items-baseline justify-center gap-[0.12em]">
          <span
            className="font-semibold tracking-tight text-texte"
            style={{ fontSize: `clamp(0.85rem, ${(26 * serrage).toFixed(1)}cqw, 2.2rem)` }}
          >
            {valeur}
          </span>
          {unite && (
            <span
              className="font-medium text-texte-doux"
              style={{ fontSize: 'clamp(0.5rem, 10cqw, 0.85rem)' }}
            >
              {unite}
            </span>
          )}
        </p>
      </div>
    </div>
  )
}
