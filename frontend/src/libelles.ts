/** Abreges d'affichage des capteurs et des grandeurs jugees.
 *
 *  Le nom complet reste celui du registre backend ; il est seulement trop
 *  long pour certains emplacements. Trois jeux, parce que la place n'est
 *  pas la meme : une bille laisse tenir un mot entier, une pilule de
 *  selection non, et le panneau du modele nomme aussi des grandeurs qui
 *  ne sont pas des capteurs.
 *
 *  Un identifiant absent de ces tables retombe sur le libelle du
 *  registre : declarer un capteur ne rend donc jamais l'ecran muet.
 */
export const LIBELLE_BILLE: Record<string, string> = {
  temperature_air: 'Température',
  temperature_sol: 'Temp. sol',
  humidite_sol_a: 'Humidité',
  humidite_sol_b: 'Humidité 2',
  humidite_air: 'Humidité air',
  luminosite: 'Lumière',
  niveau_eau: 'Eau',
}

export const LIBELLE_PILULE: Record<string, string> = {
  temperature_air: 'Temp.',
  temperature_sol: 'Temp. sol',
  humidite_sol_a: 'Humidité',
  humidite_sol_b: 'Humidité 2',
  humidite_air: 'Hum. air',
  luminosite: 'Lumière',
  niveau_eau: 'Eau',
}

/** Les grandeurs jugees par le reseau, y compris celles qui ne sortent
 *  d'aucun capteur -- l'eclairement du jour est un cumul. */
export const LIBELLE_GRANDEUR: Record<string, string> = {
  humidite_sol_a: 'Humidité du sol',
  temperature_air: 'Température',
  luminosite: 'Luminosité',
  niveau_eau: 'Réserve d’eau',
  eclairement_jour: 'Lumière reçue',
}

/** Unite d'affichage de chaque grandeur jugee. */
export const UNITE_GRANDEUR: Record<string, string> = {
  humidite_sol_a: '%',
  temperature_air: '°C',
  luminosite: '%',
  niveau_eau: '%',
  eclairement_jour: 'h',
}
