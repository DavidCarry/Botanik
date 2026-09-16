import { useEffect, useState } from 'react'
import { lireModele, type Capteur, type Modele } from './api'

// Les seuils bougent avec la temperature et la lumiere, qui evoluent en
// minutes, pas en secondes : inutile de les redemander plus souvent.
const RAFRAICHISSEMENT_MS = 30_000

/** Le reseau entraine et les seuils qu'il applique en ce moment.
 *
 *  Null tant qu'on n'a pas de reponse ; `entraine: false` si aucun modele
 *  n'est en base -- l'ecran retombe alors sur les plages du registre. */
export function useModele() {
  const [modele, setModele] = useState<Modele | null>(null)

  useEffect(() => {
    let vivant = true
    const relire = () =>
      lireModele()
        .then((m) => { if (vivant) setModele(m) })
        .catch(() => undefined)
    relire()
    const t = setInterval(relire, RAFRAICHISSEMENT_MS)
    return () => { vivant = false; clearInterval(t) }
  }, [])

  return modele
}

/** La plage a afficher pour un capteur : celle qu'a apprise le reseau
 *  quand elle existe, sinon celle ecrite dans le registre.
 *
 *  Le repli n'est pas theorique : avant le premier entrainement, et si la
 *  base ne repond pas, l'ecran doit continuer a montrer quelque chose.
 *  Il vaut aussi borne par borne -- un reseau peut avoir appris un seuil
 *  bas sans jamais basculer de l'autre cote. */
export function plage(capteur: Capteur, modele: Modele | null) {
  const s = modele?.entraine ? modele.seuils?.[capteur.id] : undefined
  if (!s) return capteur.ideal
  return {
    min: s.bas ?? capteur.ideal.min,
    max: s.haut ?? capteur.ideal.max,
  }
}
