/** Abreges d'affichage des capteurs.
 *
 *  Le nom complet reste celui du registre backend ; il est seulement trop
 *  long pour certains emplacements. Deux jeux, parce que la place n'est
 *  pas la meme : une bille laisse tenir un mot entier, une pilule de
 *  selection non.
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
