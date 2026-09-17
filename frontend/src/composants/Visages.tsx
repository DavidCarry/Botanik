import { useEffect, useState, type RefObject } from 'react'
import { useVisages } from '../useVisages'

/** Ou l'image se trouve REELLEMENT dans son cadre : sa taille affichee,
 *  et le decalage de son coin haut gauche. */
type Cadrage = { l: number; h: number; x: number; y: number }

/** Suit la place occupee par l'image dans son cadre.
 *
 *  La vue est affichee en `object-cover` : elle est agrandie jusqu'a
 *  couvrir les deux cotes du cadre, puis centree, et ce qui depasse est
 *  rogne. Une position donnee en fraction de l'IMAGE ne correspond donc
 *  pas a la meme fraction du CADRE -- il manque la partie coupee.
 *
 *  On refait donc ici le calcul du navigateur, seul moyen de poser un
 *  cadre exactement sur un visage aussi bien dans la vignette, au format
 *  libre, qu'en plein ecran.
 */
function useCadrage(image: RefObject<HTMLImageElement | null>): Cadrage | null {
  const [cadrage, setCadrage] = useState<Cadrage | null>(null)

  useEffect(() => {
    const el = image.current
    if (!el) return

    const mesurer = () => {
      const { naturalWidth: nl, naturalHeight: nh } = el
      const { width: cl, height: ch } = el.getBoundingClientRect()
      // Tant que la premiere vue n'est pas arrivee, l'image n'a pas de
      // dimensions propres : rien a poser dessus.
      if (!nl || !nh || !cl || !ch) {
        setCadrage(null)
        return
      }
      // Couvrir les deux cotes, c'est prendre le PLUS GRAND des deux
      // rapports : l'autre cote deborde alors, et c'est voulu.
      const facteur = Math.max(cl / nl, ch / nh)
      const l = nl * facteur
      const h = nh * facteur
      setCadrage({ l, h, x: (cl - l) / 2, y: (ch - h) / 2 })
    }

    mesurer()
    const observateur = new ResizeObserver(mesurer)
    observateur.observe(el)
    // Un flux n'a de dimensions qu'une fois sa premiere image recue.
    // Sans cet ecouteur, les cadres attendraient un redimensionnement de
    // la fenetre pour se poser.
    el.addEventListener('load', mesurer)
    return () => {
      observateur.disconnect()
      el.removeEventListener('load', mesurer)
    }
  }, [image])

  return cadrage
}

/** Les cadres poses sur les visages, et leur nom en dessous.
 *
 *  Du HTML par-dessus l'image, et non un dessin grave dedans : le trait
 *  reste net a toutes les tailles, le nom garde la typographie du
 *  tableau de bord, et la Pi n'a aucune image a reencoder.
 *
 *  Purement decoratif pour un lecteur d'ecran : le texte de remplacement
 *  de l'image dit deja ce qu'elle montre, et des noms flottants lus hors
 *  contexte n'ajouteraient que du bruit.
 */
export default function Visages({
  image,
}: { image: RefObject<HTMLImageElement | null> }) {
  const visages = useVisages()
  const cadrage = useCadrage(image)

  if (!cadrage || visages.length === 0) return null

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0">
      {visages.map((v, i) => (
        <div
          // La position dans la liste sert de cle : c'est ce qui permet
          // au meme cadre de GLISSER d'une image a la suivante plutot
          // que de disparaitre et reapparaitre ailleurs.
          key={i}
          className="absolute rounded-carte border border-accent-vif/85
                     transition-all duration-100 ease-linear"
          style={{
            left: cadrage.x + v.x * cadrage.l,
            top: cadrage.y + v.y * cadrage.h,
            width: v.l * cadrage.l,
            height: v.h * cadrage.h,
          }}
        >
          <span
            className="absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap
                       rounded-carte bg-black/60 px-1.5 py-0.5 text-nano font-medium
                       tracking-etiquette text-accent-vif backdrop-blur-sm"
          >
            {v.nom}
          </span>
        </div>
      ))}
    </div>
  )
}
