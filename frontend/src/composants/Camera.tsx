import { useEffect, useState } from 'react'
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

/** L'adresse de la vue a afficher.
 *
 *  Un FLUX et non des images redemandees une par une. Redemander une
 *  image toutes les cent millisecondes plafonne a la cadence des
 *  allers-retours HTTP, et chaque requete recommence tout : ca saccade.
 *
 *  Ici le navigateur ouvre une seule connexion et recoit les images a
 *  mesure qu'elles arrivent -- le vieux `multipart/x-mixed-replace` des
 *  cameras de surveillance. Une balise `img` l'affiche sans une ligne de
 *  JavaScript, et sans clignoter entre deux vues.
 *
 *  L'horodatage ne sert qu'a l'ouverture : il garantit une connexion
 *  neuve quand la camera revient apres une coupure, plutot qu'une
 *  reprise d'un flux que le navigateur croit encore valide. */
function useVue(enDirect: boolean) {
  const [depuis] = useState(() => Date.now())
  return enDirect ? `/api/camera.mjpg?t=${depuis}` : SOURCE
}

/** Equerres de cadrage, la signature d'un moniteur de surveillance. */
const COINS = [
  'left-2 top-2 border-l border-t',
  'right-2 top-2 border-r border-t',
  'left-2 bottom-2 border-b border-l',
  'right-2 bottom-2 border-b border-r',
]

function Habillage({ compact, enDirect }: { compact: boolean; enDirect: boolean }) {
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
        {/* La pastille rouge n'apparait QUE si la camera produit
            vraiment des images. Sur une photo fixe, elle ferait croire a
            un direct -- et se retournerait contre nous a la premiere
            question du jury. */}
        {enDirect ? (
          <span aria-hidden className="size-2 shrink-0 rounded-pilule bg-critique" />
        ) : (
          <LuVideoOff size={11} className="shrink-0 text-texte-faible" />
        )}
        <span className="text-nano font-medium tracking-etiquette text-texte-doux">
          LENTILLE CAM
        </span>
        {/* En vignette, la mention ne tiendrait pas. */}
        {!compact && (
          <span className={`text-nano tracking-etiquette ${
            enDirect ? 'text-critique' : 'text-texte-faible'
          }`}>
            {enDirect ? '· EN DIRECT' : '· HORS LIGNE'}
          </span>
        )}
      </div>

      {!compact && !enDirect && (
        <span className="pointer-events-none absolute bottom-3 right-3 rounded-carte bg-black/55 px-2 py-1 text-nano tabular-nums tracking-etiquette text-texte-faible backdrop-blur-sm">
          {PRISE_DE_VUE}
        </span>
      )}
    </>
  )
}

/** La vue, posee sous la liste de pilotage.
 *
 *  Au grand ecran elle remplit le bloc qui l'accueille -- c'est lui qui
 *  fixe la part de hauteur qui lui revient. Son format est donc libre,
 *  et l'image le remplit sans se deformer, quitte a etre rognee.
 *  Sur mobile, ou rien ne contraint la hauteur, elle reprend le format
 *  d'un moniteur. */
export default function Camera({
  onAgrandir, enDirect,
}: { onAgrandir: () => void; enDirect: boolean }) {
  const vue = useVue(enDirect)
  return (
    <button
      type="button"
      onClick={onAgrandir}
      aria-label="Agrandir la vue de la caméra"
      className="group relative aspect-video w-full overflow-hidden rounded-carte
                 border border-bordure bg-black transition-colors duration-200
                 hover:border-bordure-forte
                 md:aspect-auto md:h-full"
    >
      <img
        src={vue}
        alt={enDirect ? 'Vue en direct de la serre'
          : 'Le châssis de la serre, photographié en salle'}
        className="size-full object-cover opacity-80"
      />
      <Habillage compact enDirect={enDirect} />

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

/** La meme vue, en grand.
 *
 *  Le cadre occupe la place disponible et l'image le REMPLIT : elle est
 *  rognee sur un bord plutot que posee au milieu de bandes noires. Les
 *  proportions sont conservees -- on perd un peu de champ, jamais la
 *  geometrie.
 */
export function CameraPleine({
  onFermer, enDirect,
}: { onFermer: () => void; enDirect: boolean }) {
  const vue = useVue(enDirect)

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
        className="apparition relative h-[86dvh] w-full max-w-6xl overflow-hidden
                   rounded-bloc border border-bordure bg-black"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Vue de la caméra"
      >
        <img
          src={vue}
          alt={enDirect ? 'Vue en direct de la serre'
            : 'Le châssis de la serre, photographié en salle'}
          className="size-full object-cover opacity-90"
        />
        <Habillage compact={false} enDirect={enDirect} />

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
