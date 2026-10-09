/** Appels a l'API.
 *
 *  Deux assemblages, un seul code. Servi par la Raspberry Pi, le
 *  tableau de bord parle a l'API par des chemins RELATIFS : c'est le
 *  meme serveur qui repond, il n'y a rien a configurer. Embarquee dans
 *  l'application Android, la page vient de l'appareil : il lui faut
 *  alors l'adresse complete de la serre.
 *
 *  `VITE_API` porte cette difference. Vide -- le cas du web --, tout se
 *  comporte comme avant.
 */
export const BASE: string = import.meta.env.VITE_API ?? ''

/** Vrai quand la page ne vient pas du meme serveur que l'API. */
export const DISTANT = BASE !== ''

/** Le jeton de session de l'application.
 *
 *  Sur le web, le serveur pose un cookie `httponly`, hors de portee du
 *  JavaScript : c'est plus sur, et on n'y touche pas. Mais un cookie ne
 *  franchit pas la frontiere entre deux origines sans HTTPS, que la
 *  serre n'a pas. L'application garde donc le MEME jeton ici et le
 *  represente dans un en-tete, qui passe partout.
 */
const CLE = 'botanik.jeton'

export const jeton = () =>
  (DISTANT ? localStorage.getItem(CLE) : null) || null

export function garderJeton(valeur: string | null) {
  if (!DISTANT) return
  if (valeur) localStorage.setItem(CLE, valeur)
  else localStorage.removeItem(CLE)
}

function entetes(base?: HeadersInit): HeadersInit | undefined {
  const j = jeton()
  if (!j) return base
  return { ...(base as Record<string, string>), Authorization: `Bearer ${j}` }
}

/** Toutes les routes repondent du JSON et signalent l'echec par le code
 *  HTTP : un seul endroit pour lire l'un et verifier l'autre. */
async function json<T>(chemin: string, options?: RequestInit): Promise<T> {
  const r = await fetch(BASE + chemin, {
    ...options,
    headers: entetes(options?.headers),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json() as Promise<T>
}

/** Meme chose que `poster`, pour les methodes qui ne sont pas POST. */
function envoyer<T>(chemin: string, methode: string, corps?: unknown): Promise<T> {
  return json<T>(chemin, {
    method: methode,
    ...(corps === undefined
      ? {}
      : {
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(corps),
        }),
  })
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
  echelle: { min: number; max: number }
  /** La plage voulue par l'utilisateur, ou null s'il n'en a défini
   *  aucune. Une borne à null veut dire « ce côté est infini » :
   *  « au-dessus de 50 » est une consigne complète. */
  plage: { bas: number | null; haut: number | null } | null
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
      /** Ce qui l'a déclenché : la main, une borne franchie, ou une
       *  personne reconnue. */
      source: 'manuel' | 'seuil' | 'visage'
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

// ---------- Règles de l'utilisateur ----------

/** Ce que la serre fait quand une borne est franchie. */
export type ActionRegle =
  | { genre: 'actionneur'; cible: string; valeur: number }
  | { genre: 'ecran'; cible?: string; texte: string }

/** Une borne suit le seuil appris, vaut un nombre fixe, ou est ignorée. */
export type ModeBorne = 'ia' | 'manuel' | 'aucun'

export type BorneRegle = {
  mode: ModeBorne
  valeur: number | null
  action: ActionRegle | null
}

export type Regle = { grandeur: string; bas: BorneRegle; haut: BorneRegle }

export type GrandeurReglee = {
  id: string
  libelle: string
  unite: string
  echelle: { min: number; max: number } | null
  /** Ce que le réseau a appris, aux conditions du moment. Null : pas de
   *  modèle entraîné, les bornes « ia » n'ont alors rien à suivre. */
  seuil_ia: { bas: number | null; haut: number | null } | null
  regle: Regle | null
}

export type Reglages = {
  grandeurs: GrandeurReglee[]
  actionneurs: { id: string; libelle: string }[]
  /** La clarté à partir de laquelle la lumière compte dans le cumul du
   *  jour, dans l'unité du capteur de luminosité.
   *
   *  Ce n'est pas une borne : elle ne déclenche rien. Elle dit ce que
   *  « douze heures de lumière » veut dire. */
  lumiere_utile: number
}

export const lireReglages = () => json<Reglages>('/api/regles')

export const poserRegle = (grandeur: string, bas: BorneRegle, haut: BorneRegle) =>
  envoyer<{ ok: boolean }>(`/api/regles/${grandeur}`, 'PUT', { bas, haut })

export const retirerRegle = (grandeur: string) =>
  envoyer<{ ok: boolean }>(`/api/regles/${grandeur}`, 'DELETE')

export const poserLumiereUtile = (utile: number) =>
  envoyer<{ ok: boolean }>('/api/eclairement', 'PUT', { utile })

// ---------- Santé de la chaîne ----------

export type Sante = {
  /** Age de la derniere mesure archivee, en secondes. Null : la base est
   *  vide, ou injoignable. */
  archivage_s: number | null
  archivage_ok: boolean
  /** Age de la derniere sauvegarde, en heures. Null : aucune. */
  sauvegarde_h: number | null
  /** Age de la derniere prise de vue, en secondes. Null : pas de camera. */
  camera_s: number | null
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
  /** Les champs ci-dessus qui n'ont PAS pu être mesurés et ont été
   *  remplacés par une valeur plausible. */
  simules: string[]
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
    const d = await poster<{ identifiant: string; jeton: string }>(
      '/api/connexion', { identifiant, mot_de_passe: motDePasse },
    )
    // Le navigateur a déjà son cookie et ignore ce jeton ; l'application,
    // elle, n'a que lui.
    garderJeton(d.jeton)
    return d.identifiant
  } catch {
    // Le serveur ne dit pas lequel des deux est faux, et c'est voulu :
    // distinguer les deux cas renseignerait sur les comptes existants.
    throw new Error('Identifiant ou mot de passe incorrect')
  }
}

export async function seDeconnecter() {
  try {
    return await poster<{ ok: boolean }>('/api/deconnexion')
  } finally {
    // Quoi qu'il arrive côté serveur, l'appareil oublie le jeton : rester
    // connecté alors qu'on vient de se déconnecter serait pire qu'une
    // erreur réseau.
    garderJeton(null)
  }
}

// ---------- Actionneurs ----------

/** Ce qu'un afficheur doit montrer : une intention, pas un texte figé.
 *  « la température » suit la mesure ; « 23.6 °C » resterait figé. */
export type Contenu =
  /** Plusieurs capteurs : ils défilent, cinq secondes chacun. */
  | { mode: 'mesure'; capteurs: string[]; capteur?: string }
  | { mode: 'texte'; texte: string }

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
  /** Afficheurs seulement : ce qu'on leur a demandé de montrer… */
  contenu?: Contenu | null
  /** …et les deux lignes réellement écrites dessus. */
  lignes?: string[] | null
}

export const lireActionneurs = () => json<Actionneur[]>('/api/actionneurs')

export const commander = (actionneur: string, valeur: number, contenu?: Contenu) =>
  poster<{ ok: boolean }>('/api/commandes', { actionneur, valeur, contenu })

// ---------- Visages ----------

/** Un sujet de règle : une personne apprise, ou l'un des deux sujets
 *  qui ne désignent personne en particulier. */
export type Sujet = {
  id: string
  libelle: string
  /** Sujets spéciaux seulement : ce qu'ils recouvrent. */
  detail?: string
  /** Personnes seulement : combien de photos la serre a d'elles. Sa
   *  présence distingue une personne d'un sujet général. */
  references?: number
}

export type ReglagesVisages = {
  speciaux: Sujet[]
  personnes: Sujet[]
  /** Une action par sujet réglé. Un sujet absent ne déclenche rien. */
  regles: Record<string, ActionRegle | null>
  actionneurs: { id: string; libelle: string }[]
}

export const lireReglagesVisages = () => json<ReglagesVisages>('/api/visages')

export const poserRegleVisage = (sujet: string, action: ActionRegle) =>
  envoyer<{ ok: boolean }>(`/api/visages/regles/${sujet}`, 'PUT', { action })

export const retirerRegleVisage = (sujet: string) =>
  envoyer<{ ok: boolean }>(`/api/visages/regles/${sujet}`, 'DELETE')
