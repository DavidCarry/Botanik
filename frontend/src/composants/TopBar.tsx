import { useEffect, useState } from 'react'
import { LuLogIn, LuLogOut } from 'react-icons/lu'
import type { Auth } from '../useAuth'
import Logo from './Logo'

/** Barre fixe. Le flou d'arriere-plan prend appui sur les lueurs du fond
 *  et sur ce qui defile dessous : c'est ce qui la fait lire comme une
 *  plaque de verre posee sur la page, et non comme un bandeau opaque. */
export default function TopBar({
  auth, onConnexion, onSysteme, enLigne,
}: {
  auth: Auth
  onConnexion: () => void
  onSysteme: () => void
  enLigne: boolean
}) {
  const [heure, setHeure] = useState(() =>
    new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }))

  useEffect(() => {
    const t = setInterval(
      () => setHeure(new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })),
      20_000,
    )
    return () => clearInterval(t)
  }, [])

  return (
    <div className="fixed inset-x-0 top-0 z-30 px-4 sm:px-7">
      {/* Voile de flou degressif. Le masque eteint progressivement le
          `backdrop-filter` vers le bas : la barre ne se termine plus par
          une arete nette, elle se dissout dans la page. */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 -mx-4 h-24 backdrop-blur-lg sm:-mx-7"
        style={{
          maskImage: 'linear-gradient(to bottom, #000 42%, transparent 100%)',
          WebkitMaskImage: 'linear-gradient(to bottom, #000 42%, transparent 100%)',
        }}
      />

      <header className="panneau relative mx-auto flex max-w-[1600px] items-center gap-3
                   rounded-b-bloc rounded-t-none px-3.5 py-2.5 sm:px-5 sm:py-3"
        style={{ borderTop: 'none' }}>
        {/* La marque n'est pas du contenu a selectionner : curseur de
            pointage plutot que curseur de texte. */}
        <Logo taille={26} />
        <span className="cursor-default select-none leading-tight">
          <span className="block text-menu font-semibold tracking-tight text-texte">
            Botanik
          </span>
          <span className="hidden text-[0.62rem] text-texte-faible sm:block">
            Serre connectée
          </span>
        </span>

        <span className="ml-auto flex items-center gap-2 sm:gap-3">
          {/* Etat de la liaison : une pastille et un mot, jamais la
              couleur seule. Le bouton ouvre l'etat de la machine. */}
          <button
            type="button"
            onClick={onSysteme}
            aria-label="État de la machine"
            className="flex items-center gap-1.5 rounded-pilule border border-bordure bg-surface-creuse px-2.5 py-1.5 transition-all duration-200 hover:border-bordure-forte hover:bg-surface-haute"
          >
            {/* Halo et point superposes au meme centre par une grille :
                aucun des deux n'est dans le flux de l'autre. Le halo ne
                bat que si la liaison tient -- une pastille rouge qui pulse
                ressemble a une alarme, alors qu'elle ne fait que
                constater une absence. */}
            <span className="relative grid size-2 shrink-0 place-items-center">
              {enLigne && (
                <span
                  className="col-start-1 row-start-1 size-2 animate-ping rounded-pilule opacity-75"
                  style={{ background: 'var(--bon)' }}
                />
              )}
              <span
                className="col-start-1 row-start-1 size-1.5 rounded-pilule"
                style={{ background: enLigne ? 'var(--bon)' : 'var(--critique)' }}
              />
            </span>
            <span className="hidden text-micro text-texte-doux sm:inline">
              {enLigne ? 'En ligne' : 'Hors ligne'}
            </span>
            <span className="ml-1 text-micro tabular-nums text-texte-faible">{heure}</span>
          </button>

          {auth.compte ? (
            <button
              type="button"
              onClick={auth.deconnexion}
              className="flex items-center gap-1.5 rounded-pilule border border-accent/35 bg-accent-voile px-2.5 py-1.5 text-micro font-medium text-accent-vif transition-all duration-200 hover:border-accent/60 hover:bg-accent/20"
            >
              <LuLogOut size={13} />
              <span className="hidden sm:inline">{auth.compte}</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={onConnexion}
              className="flex items-center gap-1.5 rounded-pilule border border-bordure bg-surface-creuse px-2.5 py-1.5 text-micro font-medium text-texte-doux transition-all duration-200 hover:border-bordure-forte hover:bg-surface-haute hover:text-texte"
            >
              <LuLogIn size={13} />
              <span className="hidden sm:inline">Connexion</span>
            </button>
          )}
        </span>
      </header>
    </div>
  )
}
