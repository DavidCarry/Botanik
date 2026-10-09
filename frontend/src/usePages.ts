import { useEffect, useState, type RefObject } from 'react'

/** La pagination verticale du mobile : où on en est, combien il y a de
 *  pages, et comment aller à l'une d'elles.
 *
 *  Les pages ne sont pas déclarées ici, elles sont RELEVÉES dans le DOM
 *  par leur attribut `data-page`. Deux d'entre elles n'existent que pour
 *  un compte ouvert, et une liste tenue à part aurait fini par mentir
 *  sur leur nombre — c'est la même raison qui fait de `vues()` la seule
 *  source des vues du bureau.
 *
 *  Inerte au-delà de `md` : là-haut le conteneur ne défile pas, rien
 *  n'est aimanté, et la navigation qui s'en sert est masquée.
 */
export function usePages(conteneur: RefObject<HTMLElement | null>,
                         cle: unknown) {
  const [rang, setRang] = useState(0)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    const hote = conteneur.current
    if (!hote) return

    const pages = Array.from(hote.querySelectorAll<HTMLElement>('[data-page]'))
    if (pages.length === 0) return

    // Plus de la moitié visible : avec des pages hautes d'un écran, une
    // seule peut satisfaire ce seuil à la fois. Un seuil plus bas aurait
    // fait clignoter le rang au milieu de chaque glissement.
    const oeil = new IntersectionObserver(
      (entrees) => {
        // Le compte est posé ICI, dans le rappel, et non dans le corps
        // de l'effet : l'observateur se déclenche dès la mise en place,
        // donc la valeur arrive aussi vite, sans provoquer un rendu de
        // plus à chaque montage.
        setTotal(pages.length)
        for (const e of entrees) {
          if (e.isIntersecting) setRang(pages.indexOf(e.target as HTMLElement))
        }
      },
      { root: hote, threshold: 0.55 },
    )
    pages.forEach((p) => oeil.observe(p))
    return () => oeil.disconnect()
    // `cle` change quand la liste des pages change -- une connexion en
    // ajoute deux. Sans elle, l'observateur surveillerait des pages
    // disparues et en ignorerait de nouvelles.
  }, [conteneur, cle])

  // Pas de `useCallback` : la fonction ne sert qu'à des composants non
  // mémoïsés, et la mémoïser demanderait de dépendre de `conteneur.current`,
  // qui n'est pas une dépendance qu'on puisse déclarer honnêtement.
  const aller = (i: number) => {
    const pages = conteneur.current?.querySelectorAll<HTMLElement>('[data-page]')
    pages?.[i]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return { rang, total, aller }
}
