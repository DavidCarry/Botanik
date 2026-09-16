import { LuVideoOff } from 'react-icons/lu'

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

export default function Camera() {
  return (
    <div className="relative h-full w-full overflow-hidden rounded-carte border border-bordure bg-black">
      <img
        src="/serre.jpg"
        alt="Le châssis de la serre, photographié en salle"
        className="h-full w-full object-cover opacity-80"
      />

      {/* Lignes de balayage et vignettage : la signature d'un moniteur de
          surveillance, obtenue sans image supplementaire. */}
      <span aria-hidden className="camera-lignes pointer-events-none absolute inset-0" />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(120% 90% at 50% 45%, transparent 45%, rgba(2,8,5,0.55) 100%)',
        }}
      />

      {/* Equerres de cadrage. */}
      {[
        'left-2 top-2 border-l border-t',
        'right-2 top-2 border-r border-t',
        'left-2 bottom-2 border-b border-l',
        'right-2 bottom-2 border-b border-r',
      ].map((coin) => (
        <span
          key={coin}
          aria-hidden
          className={`pointer-events-none absolute size-4 border-texte/35 ${coin}`}
        />
      ))}

      <div className="absolute left-4 top-4 flex items-center gap-1.5 rounded-carte bg-black/55 px-2 py-1 backdrop-blur-sm">
        <LuVideoOff size={11} className="shrink-0 text-texte-faible" />
        <span className="text-[0.6rem] font-medium tracking-[0.18em] text-texte-doux">
          LENTILLE CAM
        </span>
        <span className="text-[0.6rem] tracking-[0.1em] text-texte-faible">
          · HORS LIGNE
        </span>
      </div>

      <span className="absolute bottom-4 right-4 rounded-carte bg-black/55 px-2 py-1 text-[0.6rem] tabular-nums tracking-[0.1em] text-texte-faible backdrop-blur-sm">
        {PRISE_DE_VUE}
      </span>
    </div>
  )
}
