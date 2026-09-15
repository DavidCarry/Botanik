/** Les grandeurs n'ont pas la meme precision utile : 22.4 °C a du sens,
 *  6550.7 lux non. */
export function formaterValeur(valeur: number, unite: string): string {
  if (Math.abs(valeur) >= 1000) return Math.round(valeur).toLocaleString('fr-FR')
  if (unite === '°C') return valeur.toFixed(1)
  return Math.round(valeur).toString()
}

