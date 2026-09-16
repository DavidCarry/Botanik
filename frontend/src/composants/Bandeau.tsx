import { Fragment, useEffect, useState } from 'react'
import {
  LuDatabase, LuTriangleAlert, LuUserRound, LuWifi, LuWifiOff,
} from 'react-icons/lu'
import type { IconType } from 'react-icons'
import type { Auth } from '../useAuth'
import { VUES, type Vue } from '../vues'
import Logo from './Logo'

/** Trois etats, et non deux : « l'API repond » ne veut pas dire « tout va
 *  bien ». Depuis que les bulles recoivent les mesures par le flux, un
 *  collecteur arrete laisse l'ecran vivant alors que plus rien n'est
 *  enregistre -- c'est l'etat degrade.
 *
 *  Chaque etat a SON icone, et pas seulement sa couleur : un daltonien,
 *  ou un ecran mal regle, doit pouvoir les distinguer. */
export type EtatLiaison = 'en_ligne' | 'degrade' | 'hors_ligne'

const LIAISON: Record<EtatLiaison, {
  icone: IconType; couleur: string; libelle: string
}> = {
  en_ligne: { icone: LuWifi, couleur: 'var(--bon)', libelle: 'En ligne' },
  degrade: { icone: LuDatabase, couleur: 'var(--attention)', libelle: 'Archivage arrêté' },
  hors_ligne: { icone: LuWifiOff, couleur: 'var(--critique)', libelle: 'Hors ligne' },
}

/** La forme commune a TOUS les elements cliquables de la barre : les
 *  pastilles de navigation comme les boutons de droite. Un seul rond,
 *  une seule taille, une seule bordure -- c'est ce qui fait tenir la
 *  barre ensemble plutot qu'une suite de formes voisines. */
const ROND =
  'grid size-8 shrink-0 place-items-center rounded-pilule border ' +
  'transition-all duration-200'

/** Une seule taille d'icone dans toute la barre : a 14 d'un cote et 15
 *  de l'autre, les ronds se ressemblaient sans se repondre. */
const ICONE = 15

/** Et un seul rythme d'espacement entre les ronds. */
const ENTRE_RONDS = 'flex items-center gap-2.5'

/** Le fond et le contour des ronds ne bougent JAMAIS : seul ce qu'ils
 *  contiennent change de couleur. Un cercle qui se remplit attire l'oeil
 *  autant qu'une alarme, et la barre se mettrait a clignoter de partout
 *  des qu'un etat change. */
const ROND_FOND = 'border-bordure bg-surface-creuse hover:border-bordure-forte'

const ROND_NEUTRE = `${ROND_FOND} text-texte-faible hover:text-texte`

/** Fil d'etapes : une pastille par vue, reliees par un trait.
 *
 *  Le trait reste neutre en toutes circonstances -- c'est un rail, pas
 *  une jauge de progression. Seule la pastille courante s'allume.
 *
 *  Le changement de vue se fait par les fleches posees aux bords de la
 *  page, pas ici : la barre dit ou l'on est, la page sert a naviguer.
 */
function Navigation({ vue, onVue }: { vue: Vue; onVue: (v: Vue) => void }) {
  return (
    <nav
      aria-label="Vue affichée"
      // Centree dans la barre horizontale, simplement posee dans la
      // colonne : au grand format elle n'a plus rien a centrer.
      // Centree dans la barre, quelle que soit la largeur des groupes
      // qui l'encadrent : d'ou le positionnement absolu.
      className="absolute left-1/2 hidden -translate-x-1/2 items-center md:flex"
    >
      <ol className="flex items-center">
        {VUES.map((v, i) => {
          const Icone = v.icone
          return (
            <Fragment key={v.valeur}>
              {i > 0 && <span aria-hidden className="h-px w-7 bg-bordure" />}
              <li>
                <button
                  type="button"
                  onClick={() => onVue(v.valeur)}
                  aria-current={v.valeur === vue ? 'page' : undefined}
                  title={v.libelle}
                  className={`${ROND} ${v.valeur === vue ? ROND_FOND : ROND_NEUTRE}`}
                  // Meme traitement que les boutons de droite : le cercle
                  // ne se remplit jamais, seule l'icone prend la couleur.
                  // Les six ronds de la barre sont alors strictement
                  // identiques, et rien n'attire l'oeil sans raison.
                  style={v.valeur === vue ? { color: 'var(--bon)' } : undefined}
                >
                  <Icone size={ICONE} />
                  <span className="sr-only">{v.libelle}</span>
                </button>
              </li>
            </Fragment>
          )
        })}
      </ol>
    </nav>
  )
}

/** Barre fixe, en haut, a toutes les largeurs.
 *
 *  Le flou d'arriere-plan prend appui sur les lueurs du fond et sur ce
 *  qui defile dessous : c'est ce qui la fait lire comme une plaque de
 *  verre posee sur la page, et non comme un bandeau opaque. */
export default function Bandeau({
  auth, onConnexion, onSysteme, onAlertes, liaison, alertes, vue, onVue,
}: {
  auth: Auth
  onConnexion: () => void
  onSysteme: () => void
  onAlertes: () => void
  liaison: EtatLiaison
  /** Nombre de problemes en cours. */
  alertes: number
  vue: Vue
  onVue: (v: Vue) => void
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

  const etat = LIAISON[liaison]
  const IconeLiaison = etat.icone

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

      <header className="panneau barre-soudee relative mx-auto flex max-w-page
                   items-center gap-3 rounded-b-bloc rounded-t-none
                   px-3.5 py-2.5 sm:px-5 sm:py-3">
        {/* La marque n'est pas du contenu a selectionner : curseur de
            pointage plutot que curseur de texte. */}
        <Logo taille={26} />
        <span className="cursor-default select-none leading-tight">
          <span className="block text-menu font-semibold tracking-tight text-texte">
            Botanik
          </span>
          <span className="hidden text-micro leading-tight text-texte-faible sm:block">
            Serre connectée
          </span>
        </span>

        <Navigation vue={vue} onVue={onVue} />

        <span className={`ml-auto ${ENTRE_RONDS}`}>
          {/* L'heure sort des boutons : elle ne se clique pas, elle n'a
              donc rien a faire dans une forme cliquable. */}
          <span className="cursor-default select-none text-micro tabular-nums text-texte-faible">
            {heure}
          </span>

          <button
            type="button"
            onClick={onAlertes}
            aria-label={alertes > 0 ? `${alertes} alerte(s) en cours` : 'Aucune alerte'}
            className={`${ROND} ${alertes > 0 ? ROND_FOND : ROND_NEUTRE}`}
            style={alertes > 0 ? { color: 'var(--critique)' } : undefined}
          >
            <LuTriangleAlert size={ICONE} />
          </button>

          <button
            type="button"
            onClick={onSysteme}
            aria-label={`${etat.libelle} — état de la machine`}
            title={etat.libelle}
            className={`${ROND} border-bordure bg-surface-creuse hover:border-bordure-forte`}
            style={{ color: etat.couleur }}
          >
            <IconeLiaison size={ICONE} />
          </button>

          {/* Connecte : l'initiale du compte. Sinon : une silhouette.
              Le meme rond dans les deux cas, pour que la barre ne change
              pas de geometrie a la connexion. */}
          <button
            type="button"
            onClick={auth.compte ? auth.deconnexion : onConnexion}
            aria-label={auth.compte ? `Déconnecter ${auth.compte}` : 'Se connecter'}
            title={auth.compte ?? 'Se connecter'}
            className={`${ROND} ${auth.compte ? ROND_FOND : ROND_NEUTRE}`}
            // Le meme vert que le wifi en ligne, et non l'accent du
            // projet : plus clair, ce dernier virait au blanc a la taille
            // d'une initiale.
            style={auth.compte ? { color: 'var(--bon)' } : undefined}
          >
            {auth.compte ? (
              <span className="text-micro font-semibold uppercase leading-none">
                {auth.compte[0]}
              </span>
            ) : (
              <LuUserRound size={ICONE} />
            )}
          </button>
        </span>
      </header>
    </div>
  )
}
