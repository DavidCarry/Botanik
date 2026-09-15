export type Mesure = { valeur: number; unite: string; ts: string }

export type Capteur = {
  id: string
  libelle: string
  unite: string
  ideal: { min: number; max: number }
  echelle: { min: number; max: number }
  mesure: Mesure | null
}

// Chemin relatif : en developpement Vite proxifie vers :8000, en production
// c'est le meme serveur qui repond. Aucune URL a configurer.
export async function lireCapteurs(): Promise<Capteur[]> {
  const r = await fetch('/api/capteurs')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export type Point = { ts: string; valeur: number }
export type Fenetre = '1j' | '1s' | '1m'

export async function lireHistorique(
  capteur: string,
  fenetre: Fenetre,
): Promise<Point[]> {
  const r = await fetch(`/api/mesures?capteur=${capteur}&fenetre=${fenetre}`)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  const d = await r.json()
  return d.points
}

export type EtatSysteme = {
  horloge: string
  date: string
  temperature_cpu: number | null
  charge_cpu: number
  coeurs: number
  memoire: { utilisee_go: number; totale_go: number; part: number }
  disque: { utilise_go: number; total_go: number; part: number }
  en_ligne_s: number
}

export async function lireSysteme(): Promise<EtatSysteme> {
  const r = await fetch('/api/systeme')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function lireCompte(): Promise<string | null> {
  const r = await fetch('/api/moi')
  if (!r.ok) return null
  return (await r.json()).identifiant
}

export async function seConnecter(identifiant: string, motDePasse: string) {
  const r = await fetch('/api/connexion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifiant, mot_de_passe: motDePasse }),
  })
  if (!r.ok) throw new Error('Identifiant ou mot de passe incorrect')
  return (await r.json()).identifiant as string
}

export async function seDeconnecter() {
  await fetch('/api/deconnexion', { method: 'POST' })
}

export async function commander(actionneur: string, valeur: number) {
  const r = await fetch('/api/commandes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ actionneur, valeur }),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
}
