import type { Etat } from './composants/Tuile'

/** Les grandeurs n'ont pas la meme precision utile : 22.4 °C a du sens,
 *  6550.7 lux non. */
export function formaterValeur(valeur: number, unite: string): string {
  if (Math.abs(valeur) >= 1000) return Math.round(valeur).toLocaleString('fr-FR')
  if (unite === '°C') return valeur.toFixed(1)
  return Math.round(valeur).toString()
}

export function etatDe(
  valeur: number,
  ideal: { min: number; max: number },
  echelle: { min: number; max: number },
): { etat: Etat; texte: string } {
  if (valeur >= ideal.min && valeur <= ideal.max) {
    return { etat: 'bon', texte: 'Dans la plage idéale' }
  }

  const amplitude = echelle.max - echelle.min
  const ecart =
    valeur < ideal.min ? ideal.min - valeur : valeur - ideal.max
  const grave = ecart > amplitude * 0.2

  const sens = valeur < ideal.min ? 'Sous' : 'Au-dessus de'
  return {
    etat: grave ? 'critique' : 'attention',
    texte: `${sens} la plage idéale`,
  }
}

export function depuis(iso: string): string {
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `il y a ${s} s`
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`
  return `il y a ${Math.floor(s / 3600)} h`
}
