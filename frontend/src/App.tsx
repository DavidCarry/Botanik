import { useRef, useState } from 'react'
import { LuCpu, LuTriangleAlert } from 'react-icons/lu'
import Actionneurs from './composants/Actionneurs'
import Alertes from './composants/Alertes'
import Bandeau, { type EtatLiaison } from './composants/Bandeau'
import Bloc from './composants/Bloc'
import Camera, { CameraPleine } from './composants/Camera'
import Connexion from './composants/Connexion'
import Courbes, { EnTeteCourbes } from './composants/Courbes'
import Declencheurs from './composants/Declencheurs'
import Evenements from './composants/Evenements'
import FlechesVue from './composants/FlechesVue'
import Fond from './composants/Fond'
import InviteDefilement from './composants/InviteDefilement'
import Mesures from './composants/Mesures'
import NavPages from './composants/NavPages'
import Regles from './composants/Regles'
import Modale from './composants/Modale'
import Modele from './composants/Modele'
import Systeme from './composants/Systeme'
import { usePages } from './usePages'
import { useAuth } from './useAuth'
import { useAlertes } from './useAlertes'
import { useCourbes } from './useCourbes'
import { useSante } from './useSante'
import { vues as vuesDe, type Vue } from './vues'

// Marges identiques pour les deux vues : elles doivent se superposer
// exactement pendant le glissement, sinon le contenu semble sauter au
// changement de page.
// Les marges laterales s'elargissent des la tablette pour degager les
// fleches de changement de vue, posees aux bords de la page. Au-dela, le
// cadre ne change plus : tablette et bureau montrent la meme chose.
// La marge GAUCHE est plus large que la droite sous `md` : c'est la
// colonne de pastilles qui s'y loge, et sans elle les cartes passaient
// dessous. Des la tablette les pastilles disparaissent, et les marges
// redeviennent egales.
const CADRE = 'w-full shrink-0 pl-9 pr-4 sm:pl-12 sm:pr-8 ' +
              'md:h-full md:px-[4.75rem] md:py-4'

/** Une page du mobile : exactement un ecran, aimantee, degagee de la
 *  barre qui flotte au-dessus et de la fleche posee en bas.
 *
 *  Au-dela de `md`, l'enveloppe DISPARAIT -- `display: contents` la
 *  retire de la mise en page, et ses enfants redeviennent les cellules
 *  de la grille comme s'il n'y avait jamais eu de page. Le bureau n'est
 *  donc touche par rien de tout ceci : il glisse lateralement, sans le
 *  moindre defilement, exactement comme avant.
 *
 *  Une page porte une ou plusieurs sections ENTIERES, jamais une moitie
 *  de section. Celles qui sont trop longues -- les reglages, les
 *  visages -- defilent a l'interieur : un defilement, et un seul. */
//  `snap-always` est ce qui fait qu'on avance d'UNE page a la fois :
//  sans lui, un geste un peu vif emporte l'elan par-dessus plusieurs
//  points d'aimantation et on se retrouve a la derniere page. Avec lui,
//  le defilement a interdiction de franchir un point sans s'y arreter.
const PAGE = 'h-[100dvh] snap-start snap-always pt-[4.2rem] pb-5 ' +
             'sm:pt-[4.6rem] sm:pb-7 md:[display:contents]'

export default function App() {
  const auth = useAuth()
  const courbes = useCourbes()
  const { sante, joignable } = useSante()
  const alertes = useAlertes()
  const [vue, setVue] = useState<Vue>('mesures')
  const [connexionOuverte, setConnexionOuverte] = useState(false)
  const [systemeOuvert, setSystemeOuvert] = useState(false)
  const [alertesOuvertes, setAlertesOuvertes] = useState(false)
  const [cameraOuverte, setCameraOuverte] = useState(false)
  const defilement = useRef<HTMLDivElement>(null)

  // Tant qu'on n'a pas de reponse, on ne crie pas : la premiere lecture
  // est en vol, et un echec basculera l'etat en moins d'une seconde.
  // Une seule liste pour la navigation, les fleches et le glissement.
  const vues = vuesDe(Boolean(auth.compte))

  // Se deconnecter depuis les reglages laisserait sur une page devenue
  // invisible. On retombe sur la premiere vue en la CALCULANT plutot
  // qu'en corrigeant l'etat apres coup : un rendu de moins, et pas de
  // clignotement sur la page qui disparait.
  const visible = vues.some((v) => v.valeur === vue) ? vue : vues[0].valeur
  const rang = Math.max(0, vues.findIndex((v) => v.valeur === visible))

  // La camera est « en direct » tant qu'elle produit des images. Sans
  // vue recente, l'ecran retombe sur la photo du chassis et le dit.
  const cameraEnDirect = sante?.camera_s != null

  // Les pages du mobile sont relevees dans le DOM : se connecter en
  // ajoute deux, et `vues.length` suffit a le signaler.
  const pages = usePages(defilement, vues.length)

  const liaison: EtatLiaison = !joignable
    ? 'hors_ligne'
    : sante && !sante.archivage_ok
      ? 'degrade'
      : 'en_ligne'

  return (
    <div className="h-dvh overflow-hidden">
      <Fond />
      <Bandeau
        auth={auth}
        liaison={liaison}
        alertes={alertes.length}
        onAlertes={() => setAlertesOuvertes(true)}
        vue={visible}
        onVue={setVue}
        vues={vues}
        onConnexion={() => setConnexionOuverte(true)}
        onSysteme={() => setSystemeOuvert(true)}
      />

      {/* Un seul balisage pour les deux formats. Des la tablette, les
          vues glissent lateralement sans defiler. Sur mobile, elles se
          decoupent en PAGES d'un ecran, aimantees : on ne defile plus
          librement, on passe d'une page a la suivante.

          C'est le conteneur ci-dessous qui defile, et lui seul. Il
          remplace le defilement de la fenetre, qui se melait a celui de
          chaque bloc -- deux defilements concurrents, dont aucun n'allait
          ou l'on croyait.

          Le retrait du haut appartient aux pages et non au conteneur :
          chacune doit faire un ecran exactement, barre comprise. */}
      <div
        ref={defilement}
        className="h-dvh snap-y snap-mandatory overflow-y-auto
                   overscroll-y-contain md:snap-none md:overflow-hidden
                   md:pt-[4.6rem]"
      >
        <div
          className="mx-auto flex max-w-page flex-col
                     md:h-full md:max-w-none md:flex-row
                     md:[translate:var(--glissement)_0]
                     md:transition-[translate] md:duration-500 md:ease-[var(--ease-doux)]"
          style={{
            '--glissement': `${-rang * 100}%`,
          } as React.CSSProperties}
        >
          {/* Vue 1 : l'etat des lieux. Ce que les sondes mesurent, et ce
              que les actionneurs en font -- les deux cote a cote, parce
              qu'on ne lit pas l'un sans l'autre : une pompe qui tourne
              n'a de sens qu'en regard d'un sol trop sec. */}
          <section className={CADRE}>
            <div className="mx-auto grid h-full max-w-page
                            md:grid-cols-[62fr_38fr] md:gap-x-8">
              {/* Page mobile : les mesures, et sous elles l'invite a
                  passer a la suite. L'invite vit DANS cette page, donc
                  elle s'en va avec elle -- rien a ecouter, rien a
                  eteindre. */}
              <div data-page className={`${PAGE} flex flex-col`}>
                <Bloc titre="Mesures" className="min-h-0 flex-1">
                  <Mesures />
                </Bloc>
                <InviteDefilement />
              </div>

              {/* Le pilotage, et sous lui ce que la camera voit : on
                  commande un actionneur en regardant ce qu'il fait. Les
                  deux tiennent sur une meme page mobile, pour la meme
                  raison qu'ils partagent une colonne au bureau.

                  La camera occupe une part FIXE de la colonne : sinon une
                  liste d'actionneurs un peu longue la reduisait a un
                  bandeau. C'est la liste qui defile quand la place
                  manque. Jamais plus haute que large non plus -- d'ou le
                  plafond, mesure sur la largeur de la colonne (`@container`)
                  et augmente de la hauteur de l'en-tete. */}
              <div data-page className={PAGE}>
                <div className="@container flex h-full flex-col gap-6 md:min-h-0">
                  <Actionneurs connecte={Boolean(auth.compte)} />
                  <Bloc titre="Caméra"
                        className="shrink-0 md:h-[42%] md:max-h-[calc(100cqw+1.8rem)]">
                    <Camera onAgrandir={() => setCameraOuverte(true)}
                            enDirect={cameraEnDirect} />
                  </Bloc>
                </div>
              </div>
            </div>
          </section>

          {/* Vue 2 : l'analyse. La courbe tient la colonne de gauche, le
              journal et le modele se partagent la droite. Le pilotage
              n'est plus ici : il vit aupres des mesures, ou il se lit en
              regard de ce qui l'a declenche. */}
          <section className={CADRE}>
            <div className="mx-auto grid h-full max-w-page
                            md:grid-cols-[58fr_42fr] md:grid-rows-2 md:gap-x-8 md:gap-y-5">
              <div data-page className={PAGE}>
                <Bloc titre="Courbes" actions={<EnTeteCourbes etat={courbes} />}
                      className="h-full md:row-span-2">
                  <Courbes etat={courbes} />
                </Bloc>
              </div>

              {/* Deux sections courtes sur une meme page : le journal
                  prend la place qui reste, le modele ce qu'il lui faut.
                  Au bureau elles retrouvent leurs deux rangees, l'une
                  au-dessus de l'autre. */}
              <div data-page className={`${PAGE} flex flex-col gap-6`}>
                <Bloc titre="Journal" className="min-h-0 flex-1">
                  <Evenements />
                </Bloc>

                <Bloc titre="Modèle" className="shrink-0 md:min-h-0">
                  <Modele />
                </Bloc>
              </div>
            </div>
          </section>

          {/* Vue 3 : le reglage de la serre. Reservee aux comptes
              ouverts -- elle ne se consulte pas, elle agit. */}
          {auth.compte && (
            <section className={CADRE}>
              <div className="mx-auto h-full max-w-page">
                {/* Trop longue pour un ecran, et on ne la coupe pas :
                    c'est la seule page qui defile a l'interieur. */}
                <div data-page className={PAGE}>
                  <Regles />
                </div>
              </div>
            </section>
          )}

          {/* Vue 4 : les visages, et ce qu'ils declenchent.
              Sa propre page plutot qu'une colonne des reglages : les deux
              listes sont longues, et les mettre cote a cote enfermait
              chacune dans un demi-ecran qui defilait pour son compte. */}
          {auth.compte && (
            <section className={CADRE}>
              <div className="mx-auto h-full max-w-page">
                {/* Longue elle aussi, et pour la meme raison gardee
                    d'un seul tenant. */}
                <div data-page className={PAGE}>
                  <Declencheurs />
                </div>
              </div>
            </section>
          )}
        </div>
      </div>

      <FlechesVue
        rang={rang}
        total={vues.length}
        onAller={(i) => setVue(vues[i].valeur)}
      />

      <NavPages rang={pages.rang} total={pages.total} onAller={pages.aller} />

      {cameraOuverte && (
        <CameraPleine onFermer={() => setCameraOuverte(false)}
                      enDirect={cameraEnDirect} />
      )}

      {alertesOuvertes && (
        <Modale
          titre="Alertes"
          sousTitre={
            alertes.length > 0
              ? `${alertes.length} problème${alertes.length > 1 ? 's' : ''} en cours`
              : 'Tout est dans les clous'
          }
          icone={<LuTriangleAlert size={16} />}
          onFermer={() => setAlertesOuvertes(false)}
        >
          <Alertes liste={alertes} />
        </Modale>
      )}

      {connexionOuverte && (
        <Connexion auth={auth} onFermer={() => setConnexionOuverte(false)} />
      )}

      {systemeOuvert && (
        <Modale
          titre="Machine"
          sousTitre="Ressources de la carte"
          icone={<LuCpu size={16} />}
          onFermer={() => setSystemeOuvert(false)}
        >
          <Systeme sante={sante} />
        </Modale>
      )}
    </div>
  )
}
