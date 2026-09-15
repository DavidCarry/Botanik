import { useEffect, type ReactNode } from 'react'
import { LuX } from 'react-icons/lu'

type Props = {
  titre: string
  sousTitre?: string
  icone: ReactNode
  onFermer: () => void
  children: ReactNode
}

/** Boite modale : le fond, le cadre de verre, l'en-tete et la fermeture.
 *  Connexion et etat machine s'appuient dessus -- un seul endroit pour
 *  l'aspect et pour le comportement clavier. */
export default function Modale({
  titre, sousTitre, icone, onFermer, children,
}: Props) {
  // Echap ferme : une boite modale qu'on ne peut quitter qu'a la souris
  // est un piege au clavier.
  useEffect(() => {
    const surTouche = (e: KeyboardEvent) => { if (e.key === 'Escape') onFermer() }
    window.addEventListener('keydown', surTouche)
    return () => window.removeEventListener('keydown', surTouche)
  }, [onFermer])

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/55 p-4 backdrop-blur-sm"
      onClick={onFermer}
      role="presentation"
    >
      <div
        className="panneau apparition w-full max-w-sm rounded-bloc p-5 sm:p-6"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={titre}
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <span className="flex items-center gap-2.5">
            <span className="grid shrink-0 place-items-center text-accent-vif">{icone}</span>
            <span className="cursor-default select-none">
              <span className="block text-menu font-semibold text-texte">{titre}</span>
              {sousTitre && (
                <span className="block text-micro text-texte-faible">{sousTitre}</span>
              )}
            </span>
          </span>
          <button
            type="button" onClick={onFermer} aria-label="Fermer"
            className="-m-1 rounded-pilule p-1.5 text-texte-faible transition-colors hover:bg-surface-haute hover:text-texte"
          >
            <LuX size={17} />
          </button>
        </div>

        {children}
      </div>
    </div>
  )
}
