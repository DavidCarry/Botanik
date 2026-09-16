/** Les grandeurs n'ont pas la meme precision utile : 22.4 °C a du sens,
 *  6550.7 lux non. */
export function formaterValeur(valeur: number, unite: string): string {
  if (Math.abs(valeur) >= 1000) return Math.round(valeur).toLocaleString('fr-FR')
  if (unite === '°C') return valeur.toFixed(1)
  return Math.round(valeur).toString()
}


/** Anciennete lisible, pour un journal ou l'instant exact importe moins
 *  que la fraicheur. */
export function depuis(iso: string): string {
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `il y a ${s} s`
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`
  if (s < 86400) return `il y a ${Math.floor(s / 3600)} h`
  return `il y a ${Math.floor(s / 86400)} j`
}
