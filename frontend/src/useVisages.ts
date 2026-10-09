import { useCallback, useEffect, useRef, useState } from 'react'
import {
  apprendreVisage, lireReglagesVisages, oublierVisage, poserRegleVisage,
  retirerRegleVisage,
  type ActionRegle, type ReglagesVisages, type VisageAppris,
} from './api'
import { useFlux, type Pousse, type Visage } from './useFlux'

/** Les visages vus devant la serre, poussés par le serveur.
 *
 *  Aucune lecture initiale, et aucune n'est nécessaire : tant qu'il y a
 *  quelqu'un devant la caméra, la liste est republiée à chaque image.
 *  Un onglet ouvert au milieu d'un passage a donc son cadre en un
 *  dixième de seconde, sans rien avoir à demander.
 */
export function useVisages(): Visage[] {
  const [visages, setVisages] = useState<Visage[]>([])

  useFlux(useCallback((p: Pousse) => {
    if (p.genre === 'visages') setVisages(p.visages)
  }, []))

  return visages
}

// Une personne apprise depuis cet écran apparait tout de suite -- on
// relit juste apres. Cette relecture periodique sert aux autres : une
// reference posee en ligne de commande, ou depuis un autre onglet.
const RAFRAICHISSEMENT_MS = 15_000

const VIDE: ReglagesVisages = {
  speciaux: [], personnes: [], regles: {}, actionneurs: [],
}

/** Qui la serre connaît, ce qu'elle en fait, et de quoi le modifier.
 *
 *  Même forme que `useRegles`, et pour la même raison : le serveur
 *  valide et complète ce qu'on lui envoie, donc c'est SA version qui
 *  doit s'afficher après un enregistrement, pas celle qu'on a saisie.
 */
export function useReglagesVisages() {
  const [reglages, setReglages] = useState<ReglagesVisages>(VIDE)
  const [occupe, setOccupe] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  const [apprentissage, setApprentissage] = useState(false)
  const [appris, setAppris] = useState<VisageAppris | null>(null)
  // Son propre motif de refus, distinct de celui des regles : les deux
  // s'affichent a des endroits differents -- celui-ci dans la carte
  // d'apprentissage, l'autre en tete de page -- et partager l'etat les
  // faisait apparaitre en double.
  const [refus, setRefus] = useState<string | null>(null)

  const vivant = useRef(true)

  const relire = useCallback(() =>
    lireReglagesVisages()
      .then((d) => { if (vivant.current) setReglages(d) })
      .catch(() => { /* la page reste sur ce qu'elle montrait */ }),
  [])

  useEffect(() => {
    vivant.current = true
    const t = setInterval(relire, RAFRAICHISSEMENT_MS)
    relire()
    return () => { vivant.current = false; clearInterval(t) }
  }, [relire])

  const agir = useCallback(async (sujet: string, faire: () => Promise<unknown>) => {
    setOccupe(sujet)
    setErreur(null)
    try {
      await faire()
      await relire()
    } catch (refus) {
      // Le serveur dit pourquoi il refuse ; le repeter vaut mieux que
      // d'annoncer un echec sans motif.
      setErreur(refus instanceof Error ? refus.message : 'Enregistrement refusé')
    } finally {
      if (vivant.current) setOccupe(null)
    }
  }, [relire])

  const enregistrer = useCallback(
    (sujet: string, action: ActionRegle) =>
      agir(sujet, () => poserRegleVisage(sujet, action)),
    [agir],
  )

  const retirer = useCallback(
    (sujet: string) => agir(sujet, () => retirerRegleVisage(sujet)),
    [agir],
  )

  /** Oublie une personne. Le compte rendu d'apprentissage qui traine
   *  encore a l'ecran ne parle peut-etre que d'elle : on l'efface. */
  const oublier = useCallback(
    (nom: string) => {
      setAppris(null)
      return agir(nom, () => oublierVisage(nom))
    },
    [agir],
  )

  /** Apprend une personne, et dit si ça a marché.
   *
   *  Son propre indicateur d'occupation plutôt que celui des sujets :
   *  `occupe` porte un identifiant de sujet, et une personne qu'on est
   *  en train d'apprendre n'en a pas encore.
   */
  const apprendre = useCallback(async (nom: string, image: string) => {
    setApprentissage(true)
    setRefus(null)
    setAppris(null)
    try {
      const vu = await apprendreVisage(nom, image)
      setAppris(vu)
      await relire()
      return true
    } catch (souci) {
      setRefus(souci instanceof Error ? souci.message : 'Apprentissage refusé')
      return false
    } finally {
      if (vivant.current) setApprentissage(false)
    }
  }, [relire])

  return { reglages, occupe, erreur, enregistrer, retirer, oublier,
           apprendre, apprentissage, appris, refus }
}
