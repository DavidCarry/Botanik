import { useState } from 'react'
import { LuLock } from 'react-icons/lu'
import type { Auth } from '../useAuth'
import Modale from './Modale'

const CHAMP =
  'rounded-carte border border-bordure bg-surface-creuse px-3 py-2 text-menu ' +
  'text-texte outline-none transition-colors focus:border-accent/50'

/** Le pilotage manuel n'apparait qu'une fois un compte ouvert -- mais
 *  c'est le serveur qui refuse les commandes : masquer les boutons ne
 *  protege rien par soi-meme. */
export default function Connexion({
  auth, onFermer,
}: { auth: Auth; onFermer: () => void }) {
  const [identifiant, setIdentifiant] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [envoi, setEnvoi] = useState(false)

  const soumettre = async (e: React.FormEvent) => {
    e.preventDefault()
    setEnvoi(true)
    setErreur(null)
    try {
      await auth.connexion(identifiant, motDePasse)
      onFermer()
    } catch (err) {
      setErreur(err instanceof Error ? err.message : 'Connexion impossible')
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <Modale
      titre="Connexion"
      sousTitre="Requise pour piloter la serre"
      icone={<LuLock size={16} />}
      onFermer={onFermer}
    >
      <form onSubmit={soumettre} className="flex flex-col gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="text-micro text-texte-doux">Identifiant</span>
          <input
            value={identifiant}
            onChange={(e) => setIdentifiant(e.target.value)}
            autoComplete="username" required className={CHAMP}
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-micro text-texte-doux">Mot de passe</span>
          <input
            type="password"
            value={motDePasse}
            onChange={(e) => setMotDePasse(e.target.value)}
            autoComplete="current-password" required className={CHAMP}
          />
        </label>

        {erreur && <p role="alert" className="text-micro text-critique">{erreur}</p>}

        <button
          type="submit" disabled={envoi}
          className="mt-1 rounded-carte bg-accent px-3 py-2.5 text-menu font-medium text-page transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {envoi ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>
    </Modale>
  )
}
