import { useState } from 'react'
import { LuCpu, LuTriangleAlert } from 'react-icons/lu'
import Actionneurs from './composants/Actionneurs'
import Alertes from './composants/Alertes'
import Bandeau, { type EtatLiaison } from './composants/Bandeau'
import Bloc from './composants/Bloc'
import Camera, { CameraPleine } from './composants/Camera'
import Connexion from './composants/Connexion'
import Courbes, { EnTeteCourbes } from './composants/Courbes'
import Evenements from './composants/Evenements'
import FlechesVue from './composants/FlechesVue'
import Fond from './composants/Fond'
import InviteDefilement from './composants/InviteDefilement'
import Mesures from './composants/Mesures'
import Modale from './composants/Modale'
import Modele from './composants/Modele'
import Serre from './composants/Serre'
import Systeme from './composants/Systeme'
import { useAuth } from './useAuth'
import { useAlertes } from './useAlertes'
import { useCourbes } from './useCourbes'
import { useSante } from './useSante'
import { VUES, type Vue } from './vues'

// Marges identiques pour les deux vues : elles doivent se superposer
// exactement pendant le glissement, sinon le contenu semble sauter au
// changement de page.
const CADRE = 'w-full shrink-0 px-4 pb-5 sm:px-8 sm:pb-7 md:h-full md:py-4 lg:py-5'

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

  // Tant qu'on n'a pas de reponse, on ne crie pas : la premiere lecture
  // est en vol, et un echec basculera l'etat en moins d'une seconde.
  const rang = VUES.findIndex((v) => v.valeur === vue)

  const liaison: EtatLiaison = !joignable
    ? 'hors_ligne'
    : sante && !sante.archivage_ok
      ? 'degrade'
      : 'en_ligne'

  return (
    <div className="min-h-dvh md:h-dvh md:overflow-hidden">
      <Fond />
      <Bandeau
        auth={auth}
        liaison={liaison}
        alertes={alertes.length}
        onAlertes={() => setAlertesOuvertes(true)}
        vue={vue}
        onVue={setVue}
        onConnexion={() => setConnexionOuverte(true)}
        onSysteme={() => setSystemeOuvert(true)}
      />

      {/* Deux vues, un seul balisage. Des la tablette elles glissent
          lateralement ; sur mobile elles s'empilent et defilent, et la
          navigation disparait -- le pouce fait deja le travail.

          Le retrait suit la barre : sous elle tant qu'elle est en haut,
          a cote d'elle une fois devenue colonne. */}
      <div className="pt-[4.2rem] sm:pt-[4.6rem] md:h-dvh md:overflow-hidden
                      lg:pl-[4.75rem] lg:pt-0">
        <div
          className="mx-auto flex max-w-[1600px] flex-col gap-9 sm:gap-11
                     md:h-full md:max-w-none md:flex-row md:gap-0
                     md:[translate:var(--glissement)_0]
                     md:transition-[translate] md:duration-500 md:ease-[var(--ease-doux)]"
          style={{
            '--glissement': `${-rang * 100}%`,
          } as React.CSSProperties}
        >
          {/* Vue 1 : tout ce qui vient de la serre elle-meme -- ce que
              les sondes mesurent, ce que la camera voit, et la maquette
              de l'installation. C'est l'etat des lieux ; l'analyse et le
              pilotage se meritent d'un geste. */}
          <section className={CADRE}>
            <div className="mx-auto grid h-full max-w-[1600px] gap-9 sm:gap-11
                            md:grid-cols-[56fr_44fr] md:grid-rows-[1fr_auto] md:gap-x-6 md:gap-y-4 lg:gap-x-8 lg:gap-y-5">
              <Bloc titre="Mesures" className="md:row-span-2">
                <div className="h-[calc(100dvh-9.5rem)] md:h-full">
                  <Mesures />
                </div>
              </Bloc>

              {/* En colonne, l'invite se glisse juste apres les bulles :
                  c'est la qu'on arrive, et c'est de la qu'on defile.
                  Masquee au grand format, elle ne prend aucune cellule. */}
              <InviteDefilement />

              <Bloc titre="Maquette">
                <div className="h-[clamp(260px,38dvh,460px)] md:h-full">
                  <Serre />
                </div>
              </Bloc>

              {/* La camera se pose en vignette, alignee a droite sous la
                  maquette. Sans titre : son encadre la nomme deja, et un
                  intitule au-dessus d'un carre de 180 px desequilibrerait
                  la colonne. */}
              <div className="flex justify-end">
                <Camera onAgrandir={() => setCameraOuverte(true)} />
              </div>
            </div>
          </section>

          {/* Vue 2 : le tableau de bord, quatre blocs. */}
          <section className={CADRE}>
            <div className="mx-auto grid h-full max-w-[1600px] gap-9 sm:gap-11
                            md:grid-cols-[58fr_42fr] md:grid-rows-2 md:gap-x-6 md:gap-y-4 lg:gap-x-8 lg:gap-y-5">
              <Bloc actions={<EnTeteCourbes etat={courbes} />}>
                <div className="h-[clamp(350px,52dvh,540px)] md:h-full">
                  <Courbes etat={courbes} />
                </div>
              </Bloc>

              <Bloc>
                <Actionneurs connecte={Boolean(auth.compte)} />
              </Bloc>

              <Bloc titre="Journal">
                <div className="h-[clamp(220px,30dvh,360px)] md:h-full">
                  <Evenements />
                </div>
              </Bloc>

              <Bloc titre="Modèle">
                <Modele />
              </Bloc>
            </div>
          </section>
        </div>
      </div>

      <FlechesVue
        rang={rang}
        total={VUES.length}
        onAller={(i) => setVue(VUES[i].valeur)}
      />

      {cameraOuverte && <CameraPleine onFermer={() => setCameraOuverte(false)} />}

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
