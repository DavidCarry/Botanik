import { useCallback, useEffect, useState } from 'react'
import { lireCompte, seConnecter, seDeconnecter } from './api'

/** Qui est connecte.
 *
 *  Le jeton vit dans un cookie httponly : le navigateur l'envoie seul, et
 *  le JavaScript de la page ne peut pas le lire. On ne conserve donc ici
 *  que l'identifiant, a seule fin d'afficher ou non le pilotage --
 *  l'autorisation reelle est verifiee par le serveur a chaque commande. */
export function useAuth() {
  const [compte, setCompte] = useState<string | null>(null)
  const [pret, setPret] = useState(false)

  useEffect(() => {
    let vivant = true
    lireCompte()
      .then((c) => { if (vivant) { setCompte(c); setPret(true) } })
      .catch(() => { if (vivant) setPret(true) })
    return () => { vivant = false }
  }, [])

  const connexion = useCallback(async (id: string, mdp: string) => {
    setCompte(await seConnecter(id, mdp))
  }, [])

  const deconnexion = useCallback(async () => {
    await seDeconnecter()
    setCompte(null)
  }, [])

  return { compte, pret, connexion, deconnexion }
}

export type Auth = ReturnType<typeof useAuth>
