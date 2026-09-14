import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { lireCapteurs, type Capteur } from './api'
import { depuis, etatDe, formaterValeur } from './format'
import Tuile from './composants/Tuile'
import {
  IconeEau, IconeHumidite, IconeLuminosite, IconeTemperature,
} from './composants/icones'

const RAFRAICHISSEMENT_MS = 5000

// L'icone est de la presentation : elle vit ici, pas dans le registre backend.
const ICONES: Record<string, ReactNode> = {
  temperature_air: <IconeTemperature />,
  temperature_sol: <IconeTemperature />,
  humidite_sol_a: <IconeHumidite />,
  humidite_sol_b: <IconeHumidite />,
  humidite_air: <IconeHumidite />,
  luminosite: <IconeLuminosite />,
  niveau_eau: <IconeEau />,
}

export default function App() {
  const [capteurs, setCapteurs] = useState<Capteur[] | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)

  useEffect(() => {
    let vivant = true

    const rafraichir = async () => {
      try {
        const data = await lireCapteurs()
        if (!vivant) return
        setCapteurs(data)
        setErreur(null)
      } catch (e) {
        if (!vivant) return
        setErreur(e instanceof Error ? e.message : 'erreur inconnue')
      }
    }

    rafraichir()
    const t = setInterval(rafraichir, RAFRAICHISSEMENT_MS)
    return () => { vivant = false; clearInterval(t) }
  }, [])

  const derniere = capteurs
    ?.map((c) => c.mesure?.ts)
    .filter((ts): ts is string => Boolean(ts))
    .sort()
    .at(-1)

  return (
    <div className="min-h-dvh bg-plane text-ink">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-8 sm:py-12">

        <header className="mb-7 flex flex-wrap items-end justify-between gap-4 sm:mb-10">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-[28px]">
              Botanik
            </h1>
            <p className="mt-1 text-sm text-muted">
              Supervision de la germination
            </p>
          </div>
          <Badge erreur={erreur} charge={capteurs !== null} derniere={derniere} />
        </header>

        <section>
          <h2 className="sr-only">Mesures</h2>

          {capteurs === null && !erreur && (
            <p className="text-sm text-muted">Chargement…</p>
          )}

          {erreur && capteurs === null && (
            <p className="rounded-xl border border-hairline bg-surface p-4 text-sm text-ink-2">
              Impossible de joindre l'API. Vérifie que le backend tourne sur
              le port 8000.
            </p>
          )}

          {capteurs && (
            <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
              {capteurs.map((c) => {
                const m = c.mesure
                const statut = m
                  ? etatDe(m.valeur, c.ideal, c.echelle)
                  : { etat: 'attention' as const, texte: 'Aucune mesure reçue' }

                return (
                  <Tuile
                    key={c.id}
                    icone={ICONES[c.id] ?? <IconeHumidite />}
                    libelle={c.libelle}
                    valeur={m ? formaterValeur(m.valeur, c.unite) : '—'}
                    unite={m ? c.unite : undefined}
                    etat={statut.etat}
                    etatTexte={statut.texte}
                    plage={
                      m
                        ? { valeur: m.valeur, min: c.echelle.min, max: c.echelle.max,
                            idealMin: c.ideal.min, idealMax: c.ideal.max }
                        : undefined
                    }
                  />
                )
              })}
            </div>
          )}
        </section>

      </div>
    </div>
  )
}

function Badge({
  erreur, charge, derniere,
}: { erreur: string | null; charge: boolean; derniere?: string }) {
  const horsLigne = Boolean(erreur)
  const couleur = horsLigne ? 'bg-critique' : charge ? 'bg-bon' : 'bg-attention'
  const texte = horsLigne
    ? 'Hors ligne'
    : charge
      ? `En ligne${derniere ? ` · ${depuis(derniere)}` : ''}`
      : 'Connexion…'

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-hairline
                     bg-surface px-3 py-1.5 text-xs text-ink-2">
      <span className="relative flex size-2">
        {!horsLigne && (
          <span className={`absolute inline-flex size-full animate-ping rounded-full ${couleur} opacity-60`} />
        )}
        <span className={`relative inline-flex size-2 rounded-full ${couleur}`} />
      </span>
      {texte}
    </span>
  )
}
