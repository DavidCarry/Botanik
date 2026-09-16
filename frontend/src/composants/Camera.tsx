import { useEffect } from 'react'
import { LuExpand, LuVideoOff, LuX } from 'react-icons/lu'

/** Vue de la serre.
 *
 *  La camera n'est pas encore installee : ce qui s'affiche est une photo
 *  du chassis, et l'habillage le dit -- pastille eteinte, mention « hors
 *  ligne », date de la prise de vue. Un point rouge clignotant sur une
 *  image fixe laisserait croire a un direct, ce qui se retournerait
 *  contre nous a la premiere question du jury.
 *
 *  Le jour ou la camera arrivera, seule la source de l'image changera :
 *  l'habillage, lui, est deja a sa place.
 */
const PRISE_DE_VUE = '16/09/2026'
const SOURCE = '/serre.jpg'

/** Equerres de cadrage, la signature d'un moniteur de surveillance. */
const COINS = [
  'left-2 top-2 border-l border-t',
  'right-2 top-2 border-r border-t',
  'left-2 bottom-2 border-b border-l',
  'right-2 bottom-2 border-b border-r',
]

function Habillage({ compact }: { compact: boolean }) {
  return (
    <>
      {/* Lignes de balayage et vignettage, obtenus sans image
          supplementaire. */}
      <span aria-hidden className="camera-lignes pointer-events-none absolute inset-0" />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(120% 90% at 50% 45%, transparent 45%, rgba(2,8,5,0.55) 100%)',
        }}
      />

      {COINS.map((coin) => (
        <span
          key={coin}
          aria-hidden
          className={`pointer-events-none absolute size-4 border-texte/35 ${coin}`}
        />
      ))}

      <div className="pointer-events-none absolute left-3 top-3 flex items-center gap-1.5 rounded-carte bg-black/55 px-2 py-1 backdrop-blur-sm">
        <LuVideoOff size={11} className="shrink-0 text-texte-faible" />
        <span className="text-[0.6rem] font-medium tracking-[0.18em] text-texte-doux">
          LENTILLE CAM
        </span>
        {/* En vignette, la mention « hors ligne » ne tiendrait pas. */}
        {!compact && (
          <span className="text-[0.6rem] tracking-[0.1em] text-texte-faible">
            · HORS LIGNE
          </span>
        )}
      </div>

      {!compact && (
        <span className="pointer-events-none absolute bottom-3 right-3 rounded-carte bg-black/55 px-2 py-1 text-[0.6rem] tabular-nums tracking-[0.1em] text-texte-faible backdrop-blur-sm">
          {PRISE_DE_VUE}
        </span>
      )}
    </>
  )
}

/** La vignette. Carree : une image de surveillance se reconnait a son
 *  cadrage autant qu'a son habillage, et un carre se pose sans deranger
 *  la mise en page. Le cadrage large est recadre par `object-cover`. */
export default function Camera({ onAgrandir }: { onAgrandir: () => void }) {
  return (
    <button
      type="button"
      onClick={onAgrandir}
      aria-label="Agrandir la vue de la caméra"
      className="group relative aspect-square w-40 shrink-0 overflow-hidden rounded-carte
                 border border-bordure bg-black transition-colors duration-200
                 hover:border-bordure-forte sm:w-44 lg:w-48"
    >
      <img
        src={SOURCE}
        alt="Le châssis de la serre, photographié en salle"
        className="size-full object-cover opacity-80"
      />
      <Habillage compact />

      {/* L'invitation n'apparait qu'au survol : en permanence, elle
          encombrerait une image deja chargee. */}
      <span className="pointer-events-none absolute inset-0 grid place-items-center
                       bg-black/40 opacity-0 transition-opacity duration-200
                       group-hover:opacity-100">
        <LuExpand size={20} className="text-texte" />
      </span>
    </button>
  )
}

/** La meme vue, en grand. */
export function CameraPleine({ onFermer }: { onFermer: () => void }) {
  // Echap ferme : une vue qu'on ne peut quitter qu'a la souris est un
  // piege au clavier.
  useEffect(() => {
    const surTouche = (e: KeyboardEvent) => { if (e.key === 'Escape') onFermer() }
    window.addEventListener('keydown', surTouche)
    return () => window.removeEventListener('keydown', surTouche)
  }, [onFermer])

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-4 backdrop-blur-sm sm:p-8"
      onClick={onFermer}
      role="presentation"
    >
      <div
        className="apparition relative max-h-full w-full max-w-5xl overflow-hidden rounded-bloc border border-bordure bg-black"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Vue de la caméra"
      >
        <img
          src={SOURCE}
          alt="Le châssis de la serre, photographié en salle"
          className="max-h-[82dvh] w-full object-contain opacity-90"
        />
        <Habillage compact={false} />

        <button
          type="button"
          onClick={onFermer}
          aria-label="Fermer"
          className="absolute right-3 top-3 grid size-8 place-items-center rounded-pilule
                     bg-black/55 text-texte-doux backdrop-blur-sm transition-colors
                     hover:bg-black/75 hover:text-texte"
        >
          <LuX size={16} />
        </button>
      </div>
    </div>
  )
}
