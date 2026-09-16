import type { Fenetre } from '../api'
import { LIBELLE_PILULE } from '../libelles'
import { plage, useModele } from '../useModele'
import type { EtatCourbes } from '../useCourbes'
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
  const modele = useModele()
  if (!etat.capteur) return null

  return (
    <Graphique
      points={etat.points}
      unite={etat.capteur.unite}
      ideal={plage(etat.capteur, modele)}
      echelle={etat.capteur.echelle}
    />
  )
}
