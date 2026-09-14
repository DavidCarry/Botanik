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
