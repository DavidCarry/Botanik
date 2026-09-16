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
import Systeme from './composants/Systeme'
import { useAuth } from './useAuth'
import { useAlertes } from './useAlertes'
import { useCourbes } from './useCourbes'
import { useSante } from './useSante'
import { VUES, type Vue } from './vues'

// Marges identiques pour les deux vues : elles doivent se superposer
// exactement pendant le glissement, sinon le contenu semble sauter au
// changement de page.
// Les marges laterales s'elargissent des la tablette pour degager les
// fleches de changement de vue, posees aux bords de la page. Au-dela, le
// cadre ne change plus : tablette et bureau montrent la meme chose.
const CADRE = 'w-full shrink-0 px-4 pb-5 sm:px-8 sm:pb-7 md:h-full md:px-[4.75rem] md:py-4'

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

          Le retrait degage la barre, qui flotte au-dessus. */}
      <div className="pt-[4.2rem] sm:pt-[4.6rem] md:h-dvh md:overflow-hidden">
        <div
          className="mx-auto flex max-w-[1600px] flex-col gap-9 sm:gap-11
                     md:h-full md:max-w-none md:flex-row md:gap-0
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
            <div className="mx-auto grid h-full max-w-[1600px] gap-9 sm:gap-11
                            md:grid-cols-[62fr_38fr] md:gap-x-8">
              <Bloc titre="Mesures" className="md:min-h-0">
                <div className="h-[calc(100dvh-9.5rem)] md:h-full">
                  <Mesures />
                </div>
              </Bloc>

              {/* Le pilotage, et sous lui ce que la camera voit : on
                  commande un actionneur en regardant ce qu'il fait.
                  La camera n'a pas de titre -- son encadre la nomme. */}
              <div className="flex flex-col gap-6 md:min-h-0">
                <Actionneurs connecte={Boolean(auth.compte)} />
                <Camera onAgrandir={() => setCameraOuverte(true)} />
              </div>
            </div>
            <InviteDefilement />
          </section>

          {/* Vue 2 : l'analyse. La courbe tient la colonne de gauche, le
              journal et le modele se partagent la droite. Le pilotage
              n'est plus ici : il vit aupres des mesures, ou il se lit en
              regard de ce qui l'a declenche. */}
          <section className={CADRE}>
            <div className="mx-auto grid h-full max-w-[1600px] gap-9 sm:gap-11
                            md:grid-cols-[58fr_42fr] md:grid-rows-2 md:gap-x-8 md:gap-y-5">
              <Bloc actions={<EnTeteCourbes etat={courbes} />} className="md:row-span-2">
                <div className="h-[clamp(350px,52dvh,540px)] md:h-full">
                  <Courbes etat={courbes} />
                </div>
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
