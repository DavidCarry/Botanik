/** Appels a l'API.
 *
 *  Chemins relatifs : en developpement Vite proxifie vers :8000, en
 *  production c'est le meme serveur qui repond. Aucune URL a configurer,
 *  et rien a changer entre le PC et la Raspberry Pi.
 */

/** Toutes les routes repondent du JSON et signalent l'echec par le code
 *  HTTP : un seul endroit pour lire l'un et verifier l'autre. */
async function json<T>(chemin: string, options?: RequestInit): Promise<T> {
  const r = await fetch(chemin, options)
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json() as Promise<T>
}

function poster<T>(chemin: string, corps?: unknown): Promise<T> {
  return json<T>(chemin, {
    method: 'POST',
    ...(corps === undefined
      ? {}
      : {
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(corps),
        }),
  })
}

// ---------- Capteurs ----------

export type Mesure = { valeur: number; unite: string; ts: string }

export type Capteur = {
  id: string
  libelle: string
  unite: string
  ideal: { min: number; max: number }
  echelle: { min: number; max: number }
  /** true : aucune sonde derrière cette valeur, elle est inventée. */
  simule: boolean
  mesure: Mesure | null
}

export type Point = { ts: string; valeur: number }
export type Fenetre = '1j' | '1s' | '1m'

export const lireCapteurs = () => json<Capteur[]>('/api/capteurs')

export async function lireHistorique(
  capteur: string,
  fenetre: Fenetre,
): Promise<Point[]> {
  const d = await json<{ points: Point[] }>(
    `/api/mesures?capteur=${capteur}&fenetre=${fenetre}`,
  )
  return d.points
}

// ---------- Journal ----------

/** Un problème en cours. Il reste ouvert même pendant que la serre y
 *  remédie — la pompe tourne, mais le sol est encore trop sec.
 *  `humaine` marque ce que la serre ne peut pas corriger seule. */
export type Alerte = {
  grandeur: string
  cote: 'bas' | 'haut'
  depuis: string
  libelle: string
  humaine: boolean
}

export const lireAlertes = () => json<Alerte[]>('/api/alertes')

/** Le journal mêle les deux : sans cela, la causalité disparaîtrait
 *  entre « sol trop sec détecté » et « arrosage activé ». */
export type Evenement =
  | {
      genre: 'commande'
      ts: string
      sujet: string
      valeur: number
      /** Qui a décidé : la main, le modèle, ou le garde-fou. */
      source: 'manuel' | 'ia' | 'securite'
    }
  | {
      genre: 'alerte'
      ts: string
      sujet: string
      cote: 'bas' | 'haut'
      /** Vrai à la détection, faux à la levée. */
      ouverture: boolean
      libelle: string
      humaine: boolean
    }

export const lireEvenements = (limite = 40) =>
  json<Evenement[]>(`/api/evenements?limite=${limite}`)

// ---------- Modèle ----------

export type Seuil = { bas: number | null; haut: number | null }

export type Modele = {
  entraine: boolean
  version?: string
  architecture?: number[]
  parametres?: number
  /** Les grandeurs que le réseau juge, dans l'ordre. */
  grandeurs?: string[]
  exactitude_test?: number
  exactitude_complete?: number
  /** Un seuil par grandeur, relus dans le réseau aux conditions du
   *  moment, donc mobiles. Une borne à null signifie que le réseau ne
   *  bascule jamais de ce côté — à voir, pas à masquer. */
  seuils?: Record<string, Seuil>
  /** Les conditions qui ont servi au balayage. */
  contexte?: Record<string, number>
  cible_lumiere_h?: number
}

export const lireModele = () => json<Modele>('/api/modele')

// ---------- Santé de la chaîne ----------

export type Sante = {
  /** Age de la derniere mesure archivee, en secondes. Null : la base est
   *  vide, ou injoignable. */
  archivage_s: number | null
  archivage_ok: boolean
  /** Age de la derniere sauvegarde, en heures. Null : aucune. */
  sauvegarde_h: number | null
}

export const lireSante = () => json<Sante>('/api/sante')

// ---------- Machine ----------

export type EtatSysteme = {
  horloge: string
  temperature_cpu: number | null
  charge_cpu: number
  coeurs: number
  memoire: { utilisee_go: number; totale_go: number; part: number }
  disque: { utilise_go: number; total_go: number; part: number }
  en_ligne_s: number
}

export const lireSysteme = () => json<EtatSysteme>('/api/systeme')

// ---------- Compte ----------

/** Null plutot qu'une erreur : ne pas etre connecte est un etat normal,
 *  pas une panne. */
export async function lireCompte(): Promise<string | null> {
  try {
    return (await json<{ identifiant: string | null }>('/api/moi')).identifiant
  } catch {
    return null
  }
}

export async function seConnecter(identifiant: string, motDePasse: string) {
  try {
    const d = await poster<{ identifiant: string }>('/api/connexion', {
      identifiant,
      mot_de_passe: motDePasse,
    })
    return d.identifiant
  } catch {
    // Le serveur ne dit pas lequel des deux est faux, et c'est voulu :
    // distinguer les deux cas renseignerait sur les comptes existants.
    throw new Error('Identifiant ou mot de passe incorrect')
  }
}

export const seDeconnecter = () => poster<{ ok: boolean }>('/api/deconnexion')

// ---------- Actionneurs ----------

export type Actionneur = {
  id: string
  libelle: string
  detail: string
  /** Secondes pendant lesquelles le modèle s'abstient, après une reprise
   *  en main. Zéro : il commande à nouveau. Pas encore affiché. */
  verrou_s: number
  /** true : rien n'est câblé derrière, l'ordre est accepté sans effet. */
  simule: boolean
  /** Etat annonce par l'actionneur lui-meme. Null : il ne s'est pas
   *  manifeste -- son service est peut-etre arrete. Ne pas savoir n'est
   *  pas la meme chose qu'etre a l'arret. */
  valeur: number | null
  ts: string | null
}

export const lireActionneurs = () => json<Actionneur[]>('/api/actionneurs')

export const commander = (actionneur: string, valeur: number) =>
  poster<{ ok: boolean }>('/api/commandes', { actionneur, valeur })
