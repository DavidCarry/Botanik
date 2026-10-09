import { LuBrain, LuCircleSlash } from 'react-icons/lu'
import { LIBELLE_GRANDEUR, UNITE_GRANDEUR } from '../libelles'
import { useModele } from '../useModele'

/** Ce que le reseau a appris.
 *
 *  Les seuils affiches ne sont pas stockes : ils sont RELUS dans le
 *  reseau a chaque appel, en le sondant aux conditions du moment. C'est
 *  pour cela qu'ils se deplacent quand il fait chaud ou clair -- deux
 *  constantes dans un fichier ne sauraient pas le faire.
 *
 *  La temperature y figure bien qu'aucun actionneur n'agisse sur elle :
 *  le reseau a appris a la juger, donc son seuil se lit au meme titre.
 */
const nombre = (v: number | null) =>
  v === null ? '—' : v >= 1000 ? Math.round(v).toLocaleString('fr-FR') : v

export default function Modele() {
  const m = useModele()

  if (m === null) {
    return <p className="text-micro text-texte-faible">Lecture du modèle…</p>
  }
  if (!m.entraine) {
    return (
      <p className="grid h-full place-items-center px-4 text-center text-micro text-texte-faible">
        Aucun modèle entraîné.<br />Lancer <code>entrainer.py</code>.
      </p>
    )
  }

  const grandeurs = m.grandeurs ?? []

  return (
    <div className="flex h-full flex-col gap-2.5">
      <div className="flex items-center gap-2">
        <LuBrain size={15} className="shrink-0 text-accent-vif" />
        <span className="text-micro font-medium text-texte">
          {m.architecture?.join(' — ')}
        </span>
        <span className="text-nano text-texte-faible">
          {m.parametres} paramètres
        </span>
        <span className="ml-auto text-micro font-medium tabular-nums text-accent-vif">
          {m.exactitude_test !== undefined
            ? `${(m.exactitude_test * 100).toFixed(1)} %`
            : '—'}
        </span>
      </div>

      {/* Un seuil par grandeur. Ceux qui ne pilotent rien sont marques :
          les afficher sans le dire laisserait croire a une action. */}
      <ul className="min-h-0 flex-1 divide-y divide-bordure overflow-y-auto">
        {grandeurs.map((g) => {
          const s = m.seuils?.[g]
          const inerte = g === 'temperature_air'

          // Le budget de lumiere s'affiche en avancement et non en
          // seuil. Son seuil EST la cible, douze heures, et l'annoncer
          // comme les autres ne dirait rien de plus que la colonne d'a
          // cote : ce qu'on veut savoir ici, c'est ou on en est.
          if (g === 'eclairement_jour') {
            return (
              <li key={g} className="flex items-center gap-2 py-1.5">
                <span className="min-w-0 flex-1 truncate text-micro text-texte-doux">
                  {LIBELLE_GRANDEUR[g] ?? g}
                </span>
                <span className="shrink-0 text-micro tabular-nums text-texte">
                  {m.contexte?.eclairement_jour?.toFixed(1) ?? '—'}
                  <span className="mx-1 text-texte-faible">sur</span>
                  {m.cible_lumiere_h}
                  <span className="ml-1 text-nano font-medium text-texte-faible">
                    h
                  </span>
                </span>
              </li>
            )
          }

          return (
            <li key={g} className="flex items-center gap-2 py-1.5">
              <span className="min-w-0 flex-1 truncate text-micro text-texte-doux">
                {LIBELLE_GRANDEUR[g] ?? g}
              </span>
              {inerte && (
                <LuCircleSlash
                  size={11}
                  className="shrink-0 text-texte-faible"
                  aria-label="jugée, mais aucun actionneur ne peut agir dessus"
                />
              )}
              <span className="shrink-0 text-micro tabular-nums text-texte">
                {nombre(s?.bas ?? null)}
                <span className="mx-1 text-texte-faible">–</span>
                {nombre(s?.haut ?? null)}
                <span className="ml-1 text-nano font-medium text-texte-faible">
                  {UNITE_GRANDEUR[g] ?? ''}
                </span>
              </span>
            </li>
          )
        })}
      </ul>

      <p className="text-nano leading-relaxed text-texte-faible">
        seuils relus dans le réseau pour{' '}
        {m.contexte?.temperature_air?.toFixed(1)} °C et{' '}
        {m.contexte?.luminosite !== undefined
          ? Math.round(m.contexte.luminosite).toLocaleString('fr-FR')
          : '—'}{' '}
        {UNITE_GRANDEUR.luminosite} · version {m.version}
      </p>
    </div>
  )
}
