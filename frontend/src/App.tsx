import { useState } from 'react'
import { LuCpu } from 'react-icons/lu'
import Actionneurs from './composants/Actionneurs'
import Connexion from './composants/Connexion'
import Courbes, { EnTeteCourbes } from './composants/Courbes'
import Fond from './composants/Fond'
import InviteDefilement from './composants/InviteDefilement'
import Mesures from './composants/Mesures'
import Modale from './composants/Modale'
import Panneau from './composants/Panneau'
import Systeme from './composants/Systeme'
import TopBar from './composants/TopBar'
import { useAuth } from './useAuth'
import { useCourbes } from './useCourbes'

export default function App() {
  const auth = useAuth()
  const courbes = useCourbes()
  const [connexionOuverte, setConnexionOuverte] = useState(false)
  const [systemeOuvert, setSystemeOuvert] = useState(false)

  // Des capteurs recus valent preuve de liaison : inutile d'interroger
  // une route de sante en plus.
  const enLigne = courbes.capteurs.length > 0

  return (
    <div className="min-h-dvh lg:h-dvh lg:overflow-hidden">
      <Fond />
      <TopBar
        auth={auth}
        enLigne={enLigne}
        onConnexion={() => setConnexionOuverte(true)}
        onSysteme={() => setSystemeOuvert(true)}
      />

      {/* Tout tient dans un ecran a partir du grand format ; en dessous,
          la page redevient une colonne qui defile. */}
      <main
        className="mx-auto grid max-w-[1600px] gap-5 px-4 pb-5 pt-[4.2rem]
                   sm:gap-8 sm:px-8 sm:pb-7 sm:pt-[4.6rem]
                   lg:h-dvh lg:grid-cols-[52fr_48fr]"
      >
        {/* Les mesures restent nues sur le fond : ce sont elles le sujet,
            les panneaux ne sont que le support. */}
        {/* En colonne, les mesures occupent l'ecran entier : on arrive
            sur l'etat de la serre, le reste se merite d'un geste. */}
        <section className="flex min-w-0 flex-col lg:min-h-0">
          {/* En colonne, une hauteur explicite ; en grille, `flex-1`
              prend le relais. Les deux ensemble se neutralisent :
              `flex-1` pose flex-basis:0 et efface la hauteur. */}
          <div className="h-[calc(100dvh-7.5rem)] lg:h-auto lg:min-h-0 lg:flex-1">
            <Mesures />
          </div>
          <InviteDefilement />
        </section>

        <section className="grid min-h-0 min-w-0 gap-9 sm:gap-11 lg:gap-6 lg:grid-rows-[1fr_auto]">
          <Panneau nu actions={<EnTeteCourbes etat={courbes} />}>
            <div className="h-[clamp(350px,52dvh,540px)] lg:h-full">
              <Courbes etat={courbes} />
            </div>
          </Panneau>

          <Panneau nu>
            <Actionneurs connecte={Boolean(auth.compte)} />
          </Panneau>
        </section>
      </main>

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
          <Systeme />
        </Modale>
      )}
    </div>
  )
}
