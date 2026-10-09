import { useEffect, useState } from 'react'
import {
  LuCheck, LuRotateCcw, LuScanFace, LuTrash2, LuUserMinus, LuUserPlus, LuUsers,
} from 'react-icons/lu'
import type { ActionRegle, Sujet, VisageAppris } from '../api'
import { useReglagesVisages } from '../useVisages'
import Bloc from './Bloc'
import EditeurAction, { CHAMP } from './EditeurAction'

/** Largeur à laquelle la photo est réduite avant d'être envoyée.
 *
 *  Le détecteur la ramène de toute façon à 640 pixels de large. Téléverser
 *  les quatre méga-octets d'une photo de téléphone ne gagnerait donc
 *  rien : on les ferait traverser le Wi-Fi pour être jetés. Le double de
 *  640 laisse de la marge si la tête n'occupe qu'une part du cadre. */
const LARGEUR_ENVOI = 1280

/** La photo, réduite et réencodée en JPEG, prête à partir.
 *
 *  Le navigateur sait décoder ce qu'il sait afficher : un HEIC d'iPhone
 *  échoue ici, et c'est pour ça que le sélecteur ne propose que des
 *  formats qu'il gère. */
function reduire(fichier: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const lecteur = new FileReader()
    lecteur.onerror = () => reject(new Error('fichier illisible'))
    lecteur.onload = () => {
      const image = new Image()
      image.onerror = () => reject(new Error(
        'image illisible — un JPEG, un PNG ou un WebP est attendu'))
      image.onload = () => {
        const facteur = Math.min(1, LARGEUR_ENVOI / image.width)
        const toile = document.createElement('canvas')
        toile.width = Math.round(image.width * facteur)
        toile.height = Math.round(image.height * facteur)
        const pinceau = toile.getContext('2d')
        if (!pinceau) {
          reject(new Error('le navigateur ne sait pas réduire l’image'))
          return
        }
        pinceau.drawImage(image, 0, 0, toile.width, toile.height)
        resolve(toile.toDataURL('image/jpeg', 0.92))
      }
      image.src = lecteur.result as string
    }
    lecteur.readAsDataURL(fichier)
  })
}

/** Apprendre une personne : un nom, une photo.
 *
 *  Ce qui part n'est gardé nulle part. Le serveur en tire les 128 nombres
 *  du visage et oublie l'image — la Pi ne porte jamais de galerie de
 *  portraits.
 *
 *  Plusieurs photos d'une même personne s'ajoutent les unes aux autres,
 *  de face puis de trois quarts : réapprendre quelqu'un ne remplace rien,
 *  ça l'affine. C'est pourquoi le compte de références est annoncé.
 */
function Apprendre({
  occupe, appris, erreur, onApprendre,
}: {
  occupe: boolean
  appris: VisageAppris | null
  erreur: string | null
  onApprendre: (nom: string, image: string) => Promise<boolean>
}) {
  const [nom, setNom] = useState('')
  const [fichier, setFichier] = useState<File | null>(null)
  const [souci, setSouci] = useState<string | null>(null)
  // Un champ de fichier ne se vide pas en changeant sa valeur : on le
  // remonte. Sans ça, le nom du fichier resterait affiché après coup.
  const [tour, setTour] = useState(0)

  const pret = nom.trim() !== '' && fichier !== null && !occupe

  const envoyer = async () => {
    if (!fichier) return
    setSouci(null)
    let image: string
    try {
      image = await reduire(fichier)
    } catch (refus) {
      setSouci(refus instanceof Error ? refus.message : 'image illisible')
      return
    }
    if (await onApprendre(nom.trim(), image)) {
      setNom('')
      setFichier(null)
      setTour((t) => t + 1)
    }
  }

  return (
    <div className="space-y-2.5 rounded-carte border border-dashed border-bordure p-3">
      <div className="flex items-center gap-2">
        <LuUserPlus size={14} className="shrink-0 text-accent-vif" />
        <span className="text-menu font-medium text-texte">
          Ajouter une personne
        </span>
      </div>

      <input
        type="text"
        value={nom}
        onChange={(e) => setNom(e.target.value)}
        placeholder="Nom"
        aria-label="Nom de la personne à apprendre"
        className={CHAMP}
      />

      <input
        key={tour}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(e) => setFichier(e.target.files?.[0] ?? null)}
        aria-label="Photo de la personne"
        className="w-full text-micro text-texte-doux
                   file:mr-3 file:rounded-pilule file:border file:border-bordure
                   file:bg-surface-creuse file:px-3 file:py-1 file:text-micro
                   file:font-medium file:text-texte-doux
                   hover:file:text-texte"
      />

      <button
        type="button"
        disabled={!pret}
        onClick={envoyer}
        className="flex items-center gap-1.5 rounded-pilule border border-bordure
                   bg-accent-voile px-3 py-1 text-micro font-medium text-accent-vif
                   transition-colors duration-200 hover:border-bordure-forte
                   disabled:cursor-not-allowed disabled:border-bordure
                   disabled:bg-transparent disabled:text-texte-faible"
      >
        <LuCheck size={13} />
        {occupe ? 'Apprentissage…' : 'Apprendre'}
      </button>

      {/* Le refus du serveur ou celui du navigateur, au même endroit :
          dans les deux cas c'est la photo qu'il faut reprendre. */}
      {(souci ?? erreur) && (
        <p role="alert" className="text-nano leading-relaxed text-critique">
          {souci ?? erreur}
        </p>
      )}

      {appris && !souci && !erreur && (
        <p className="text-nano leading-relaxed text-texte-faible">
          <span className="text-accent-vif">{appris.nom}</span> appris — visage
          de {appris.largeur}×{appris.hauteur} px, confiance{' '}
          {appris.confiance.toFixed(2)}, {appris.references} référence
          {appris.references > 1 ? 's' : ''}.
          {appris.ecartes > 0 && ` ${appris.ecartes} autre${
            appris.ecartes > 1 ? 's' : ''} visage${
            appris.ecartes > 1 ? 's' : ''} sur la photo : le plus grand a été retenu.`}
          {' '}La caméra le nommera d’ici dix secondes.
        </p>
      )}
    </div>
  )
}

/** Un sujet, et ce que la serre fait en le voyant. */
function Ligne({
  sujet, regle, actionneurs, occupe, onEnregistrer, onRetirer, onOublier,
}: {
  sujet: Sujet
  regle: ActionRegle | null
  actionneurs: { id: string; libelle: string }[]
  occupe: boolean
  onEnregistrer: (a: ActionRegle) => void
  onRetirer: () => void
  /** Personnes seulement : les sujets généraux ne s'oublient pas. */
  onOublier?: () => void
}) {
  const [action, setAction] = useState<ActionRegle | null>(regle)

  // Oublier quelqu'un est sans retour — les photos ne sont pas gardées —
  // donc le bouton s'arme avant d'agir. Et l'armement retombe tout seul :
  // un bouton laissé armé serait un piège au prochain clic distrait.
  const [arme, setArme] = useState(false)
  useEffect(() => {
    if (!arme) return
    const t = setTimeout(() => setArme(false), 5_000)
    return () => clearTimeout(t)
  }, [arme])

  // La version du serveur fait foi : dès qu'elle change, on reprend la
  // sienne plutôt que de garder une saisie devenue fausse.
  const signature = JSON.stringify(regle)
  useEffect(() => {
    setAction(regle)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature])

  const modifie = JSON.stringify(action) !== signature
  const complet = action !== null
    && (action.genre !== 'ecran' || action.texte.trim() !== '')

  return (
    // Une carte par sujet, et non des lignes filetées : la page est
    // large, et une liste pleine largeur étirait chaque sélecteur
    // d'action sur tout l'écran pour trois mots.
    <div className="space-y-2.5 rounded-carte border border-bordure p-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {sujet.references === undefined
          ? <LuUsers size={14} className="shrink-0 text-texte-faible" />
          : <LuScanFace size={14} className="shrink-0 text-accent-vif" />}
        <span className="text-menu font-medium text-texte">{sujet.libelle}</span>
        <span className="text-micro text-texte-faible">
          {sujet.detail ?? `${sujet.references} référence${
            (sujet.references ?? 0) > 1 ? 's' : ''}`}
        </span>

        <span className="ml-auto flex items-center gap-2">
          {modifie && (
            <button
              type="button"
              onClick={() => setAction(regle)}
              aria-label={`Abandonner les modifications de ${sujet.libelle}`}
              className="rounded-pilule p-1.5 text-texte-faible transition-colors
                         duration-200 hover:bg-survol hover:text-texte"
            >
              <LuRotateCcw size={14} />
            </button>
          )}
          {regle && (
            <button
              type="button"
              onClick={onRetirer}
              disabled={occupe}
              aria-label={`Retirer le déclencheur de ${sujet.libelle}`}
              className="rounded-pilule p-1.5 text-texte-faible transition-colors
                         duration-200 hover:bg-survol hover:text-critique
                         disabled:opacity-40"
            >
              <LuTrash2 size={14} />
            </button>
          )}
          {/* La corbeille ci-dessus retire le DÉCLENCHEUR, la serre
              continuant de reconnaître la personne. Celui-ci l'oublie
              pour de bon. Deux gestes différents, deux boutons. */}
          {onOublier && (arme ? (
            <button
              type="button"
              onClick={() => { setArme(false); onOublier() }}
              disabled={occupe}
              className="rounded-pilule border border-critique/50 px-2 py-1
                         text-nano font-medium text-critique transition-colors
                         duration-200 hover:bg-critique/10 disabled:opacity-40"
            >
              Oublier ?
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setArme(true)}
              disabled={occupe}
              aria-label={`Oublier ${sujet.libelle} et ses références`}
              className="rounded-pilule p-1.5 text-texte-faible transition-colors
                         duration-200 hover:bg-survol hover:text-critique
                         disabled:opacity-40"
            >
              <LuUserMinus size={14} />
            </button>
          ))}
          <button
            type="button"
            disabled={!modifie || !complet || occupe}
            onClick={() => action && onEnregistrer(action)}
            className="flex items-center gap-1.5 rounded-pilule border border-bordure
                       bg-accent-voile px-3 py-1 text-micro font-medium text-accent-vif
                       transition-colors duration-200 hover:border-bordure-forte
                       disabled:cursor-not-allowed disabled:border-bordure
                       disabled:bg-transparent disabled:text-texte-faible"
          >
            <LuCheck size={13} />
            {modifie ? 'Enregistrer' : 'À jour'}
          </button>
        </span>
      </div>

      <EditeurAction
        action={action}
        actionneurs={actionneurs}
        etiquette={`Action quand ${sujet.libelle.toLowerCase()} est là`}
        // Un visage sans action ne serait pas une règle : on la retire.
        permetAucune={false}
        onChange={setAction}
      />
    </div>
  )
}

/** Ce que la serre fait quand elle voit quelqu'un.
 *
 *  Même forme d'action que les bornes, et c'est voulu : un visage
 *  reconnu et un seuil franchi déclenchent exactement les mêmes choses.
 *  Seul le déclencheur change.
 *
 *  Les deux premiers sujets ne désignent personne en particulier et sont
 *  toujours là ; les suivants sont les personnes apprises. On en ajoute
 *  depuis la première carte, et on peut en oublier — mais le bouton
 *  s'arme avant d'agir, parce qu'aucune photo n'est gardée et qu'il
 *  faudra en reprendre une pour revenir en arrière.
 *
 *  Toute cette page n'existe que pour un visiteur connecté — c'est `App`
 *  qui ne la monte pas autrement — et la route d'apprentissage refuse de
 *  son côté sans session. L'écran et le serveur disent la même chose.
 */
export default function Declencheurs() {
  const {
    reglages, occupe, erreur, enregistrer, retirer, oublier,
    apprendre, apprentissage, appris, refus,
  } = useReglagesVisages()

  const sujets = [...reglages.speciaux, ...reglages.personnes]

  return (
    <Bloc
      titre="Visages"
      actions={erreur
        ? <span role="alert" className="text-micro text-critique">{erreur}</span>
        : <span className="text-micro text-texte-faible">
            {reglages.personnes.length === 0
              ? 'aucune personne apprise'
              : `${reglages.personnes.length} personne${
                  reglages.personnes.length > 1 ? 's' : ''} connue${
                  reglages.personnes.length > 1 ? 's' : ''}`}
          </span>}
      className="h-full md:min-h-0"
    >
      <div className="grid h-full content-start gap-3 overflow-y-auto pr-1
                      sm:grid-cols-2 xl:grid-cols-3">
        <Apprendre
          occupe={apprentissage}
          appris={appris}
          erreur={refus}
          onApprendre={apprendre}
        />

        {sujets.length === 0 ? (
          <p className="text-micro text-texte-faible">Lecture des visages…</p>
        ) : sujets.map((s) => (
          <Ligne
            key={s.id}
            sujet={s}
            regle={reglages.regles[s.id] ?? null}
            actionneurs={reglages.actionneurs}
            occupe={occupe === s.id}
            onEnregistrer={(a) => enregistrer(s.id, a)}
            onRetirer={() => retirer(s.id)}
            // `references` ne vaut quelque chose que pour une personne :
            // « quelqu'un » et « un inconnu » ne s'oublient pas.
            onOublier={s.references === undefined
              ? undefined
              : () => oublier(s.id)}
          />
        ))}
      </div>
    </Bloc>
  )
}
