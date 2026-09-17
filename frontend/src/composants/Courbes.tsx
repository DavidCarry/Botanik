import type { Fenetre } from '../api'
import { LIBELLE_PILULE } from '../libelles'
import type { EtatCourbes } from '../useCourbes'
import { useMesures } from '../useMesures'
import Graphique from './Graphique'
import Pilules from './Pilules'

const FENETRES: { valeur: Fenetre; libelle: string }[] = [
  { valeur: '1j', libelle: '1 J' },
  { valeur: '1s', libelle: '1 S' },
  { valeur: '1m', libelle: '1 M' },
]

/** Selecteurs seuls : la valeur du moment est deja lisible dans les
 *  billes, la repeter ici ferait doublon. */
export function EnTeteCourbes({ etat }: { etat: EtatCourbes }) {
  return (
    <div className="flex flex-1 flex-wrap items-center justify-end gap-x-3 gap-y-2">
      {etat.capteurs.length > 0 && (
        <Pilules
          etiquette="Mesure affichée"
          options={etat.capteurs.map((c) => ({
            valeur: c.id,
            libelle: LIBELLE_PILULE[c.id] ?? c.libelle,
          }))}
          choisi={etat.choisi}
          onChange={etat.setChoisi}
        />
      )}
      <Pilules
        etiquette="Période"
        options={FENETRES}
        choisi={etat.fenetre}
        onChange={etat.setFenetre}
      />
    </div>
  )
}

export default function Courbes({ etat }: { etat: EtatCourbes }) {
  // La liste des courbes est lue une fois au chargement ; celle des
  // mesures, elle, est tenue a jour par le flux. On y reprend donc la
  // plage, sinon une borne posee dans les reglages n'apparaitrait ici
  // qu'au prochain rechargement de la page.
  const { capteurs } = useMesures()
  const vivant = capteurs?.find((c) => c.id === etat.choisi)

  if (!etat.capteur) return null

  return (
    <Graphique
      points={etat.points}
      unite={etat.capteur.unite}
      // La plage vient de la regle posee par l'utilisateur. Aucune
      // regle, aucune ligne : la courbe se lit alors sans consigne.
      plage={vivant?.plage ?? etat.capteur.plage}
      echelle={etat.capteur.echelle}
    />
  )
}
