import { useState } from 'react'
import { LuCpu } from 'react-icons/lu'
import Actionneurs from './composants/Actionneurs'
import Bandeau, { type EtatLiaison } from './composants/Bandeau'
import Bloc from './composants/Bloc'
import Camera from './composants/Camera'
import Connexion from './composants/Connexion'
import Courbes, { EnTeteCourbes } from './composants/Courbes'
import Evenements from './composants/Evenements'
import FlechesVue from './composants/FlechesVue'
import Fond from './composants/Fond'
import InviteDefilement from './composants/InviteDefilement'
import Mesures from './composants/Mesures'
import Modale from './composants/Modale'
import Modele from './composants/Modele'
import Projet from './composants/Projet'
import Serre from './composants/Serre'
import Systeme from './composants/Systeme'
import { useAuth } from './useAuth'
import { useCourbes } from './useCourbes'
import { useSante } from './useSante'
import { VUES, type Vue } from './vues'

// Marges laterales et retrait sous la barre, identiques pour les deux
// vues : elles doivent se superposer exactement pendant le glissement,
// sinon le contenu semble sauter au changement de page.
const CADRE = 'w-full shrink-0 px-4 sm:px-8 pb-5 sm:pb-7 lg:pt-[4.6rem] lg:h-full'

export default function App() {
  const auth = useAuth()
  const courbes = useCourbes()
  const { sante, joignable } = useSante()
  const [vue, setVue] = useState<Vue>('mesures')
  const [connexionOuverte, setConnexionOuverte] = useState(false)
  const [systemeOuvert, setSystemeOuvert] = useState(false)

  // Tant qu'on n'a pas de reponse, on ne crie pas : la premiere lecture
  // est en vol, et un echec basculera l'etat en moins d'une seconde.
  const rang = VUES.findIndex((v) => v.valeur === vue)

  const liaison: EtatLiaison = !joignable
    ? 'hors_ligne'
    : sante && !sante.archivage_ok
      ? 'degrade'
      : 'en_ligne'

  return (
    <div className="min-h-dvh lg:h-dvh lg:overflow-hidden">
      <Fond />
      <Bandeau
        auth={auth}
        liaison={liaison}
        vue={vue}
        onVue={setVue}
        onConnexion={() => setConnexionOuverte(true)}
        onSysteme={() => setSystemeOuvert(true)}
      />

      {/* Deux vues, un seul balisage. Sur grand ecran elles glissent
          lateralement ; en dessous elles s'empilent et defilent, et la
          navigation disparait -- le pouce fait deja le travail. */}
      <div className="pt-[4.2rem] sm:pt-[4.6rem] lg:h-dvh lg:overflow-hidden lg:pt-0">
        <div
          className="mx-auto flex max-w-[1600px] flex-col gap-9 sm:gap-11
                     lg:h-full lg:max-w-none lg:flex-row lg:gap-0
                     lg:[translate:var(--glissement)_0]
                     lg:transition-[translate] lg:duration-500 lg:ease-[var(--ease-doux)]"
          style={{
            '--glissement': `${-rang * 100}%`,
          } as React.CSSProperties}
        >
          {/* Vue 1 : les mesures seules. C'est l'etat de la serre qu'on
              vient voir en premier ; le reste se merite d'un geste. */}
          <section className={`${CADRE} lg:flex lg:flex-col`}>
            <div className="mx-auto h-[calc(100dvh-7.5rem)] w-full max-w-[1600px] lg:h-auto lg:min-h-0 lg:flex-1">
              <Mesures />
            </div>
            <InviteDefilement />
          </section>

          {/* Vue 2 : la serre elle-meme -- sa maquette, sa camera, et ce
              que le projet cherche a faire. */}
          <section className={CADRE}>
            <div className="mx-auto grid h-full max-w-[1600px] gap-9 sm:gap-11
                            lg:grid-cols-[46fr_54fr] lg:grid-rows-2 lg:gap-x-8 lg:gap-y-5">
              <Bloc titre="Maquette" className="lg:row-span-2">
                <div className="h-[clamp(260px,34dvh,420px)] lg:h-full">
                  <Serre />
                </div>
              </Bloc>

              <Bloc titre="Caméra">
                <div className="h-[clamp(200px,28dvh,340px)] lg:h-full">
                  <Camera />
                </div>
              </Bloc>

              <Bloc titre="Le projet">
                <div className="h-[clamp(240px,30dvh,340px)] lg:h-full">
                  <Projet />
                </div>
              </Bloc>
            </div>
          </section>

          {/* Vue 3 : le tableau de bord, quatre blocs. */}
          <section className={CADRE}>
            <div className="mx-auto grid h-full max-w-[1600px] gap-9 sm:gap-11
                            lg:grid-cols-[58fr_42fr] lg:grid-rows-2 lg:gap-x-8 lg:gap-y-5">
              <Bloc actions={<EnTeteCourbes etat={courbes} />}>
                <div className="h-[clamp(350px,52dvh,540px)] lg:h-full">
                  <Courbes etat={courbes} />
                </div>
              </Bloc>

              <Bloc>
                <Actionneurs connecte={Boolean(auth.compte)} />
              </Bloc>

              <Bloc titre="Journal">
                <div className="h-[clamp(220px,30dvh,360px)] lg:h-full">
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
