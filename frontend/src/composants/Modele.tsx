import { LuBrain } from 'react-icons/lu'
import { useModele } from '../useModele'

/** Ce que le reseau a appris.
 *
 *  Les seuils affiches ne sont pas stockes quelque part : ils sont RELUS
 *  dans le reseau a chaque appel, en le sondant aux conditions du moment.
 *  C'est pour cela qu'ils se deplacent quand il fait chaud ou clair --
 *  deux constantes dans un fichier ne sauraient pas le faire.
 */
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

  const s = m.seuils
  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex items-center gap-2">
        <LuBrain size={15} className="shrink-0 text-accent-vif" />
        <span className="text-micro font-medium text-texte">
          {m.architecture?.join(' — ')}
        </span>
        <span className="text-[0.6rem] text-texte-faible">
          {m.parametres} paramètres
        </span>
        <span className="ml-auto text-micro font-medium tabular-nums text-accent-vif">
          {m.exactitude_test !== undefined
            ? `${(m.exactitude_test * 100).toFixed(1)} %`
            : '—'}
        </span>
      </div>

      {/* Les deux seuils, tels qu'ils s'appliquent maintenant. */}
      <div className="grid flex-1 place-items-center">
        {s && s.bas !== null && s.haut !== null ? (
          <div className="text-center">
            <p className="text-micro text-texte-faible">
              Humidité du sol — plage décidée
            </p>
            <p className="mt-1 flex items-baseline justify-center gap-2">
              <span className="text-[1.6rem] font-semibold tabular-nums text-texte">
                {s.bas}
              </span>
              <span className="text-menu text-texte-faible">à</span>
              <span className="text-[1.6rem] font-semibold tabular-nums text-texte">
                {s.haut}
              </span>
              <span className="text-menu font-medium text-texte-doux">%</span>
            </p>
            {m.conditions && (
              <p className="mt-1.5 text-[0.6rem] text-texte-faible">
                pour {m.conditions.temperature_air.toFixed(1)} °C et{' '}
                {Math.round(m.conditions.luminosite).toLocaleString('fr-FR')} lux
              </p>
            )}
          </div>
        ) : (
          <p className="text-micro text-attention">
            Le modèle ne bascule jamais — à réentraîner
          </p>
        )}
      </div>

      <p className="text-[0.6rem] text-texte-faible">
        version {m.version} · exactitude mesurée sur un jeu de test
      </p>
    </div>
  )
}
