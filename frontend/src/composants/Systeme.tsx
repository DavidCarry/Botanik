import { useEffect, useState } from 'react'
import { LuClock, LuCpu, LuHardDrive, LuMemoryStick, LuThermometer } from 'react-icons/lu'
import { lireSysteme, type EtatSysteme } from '../api'
import Barre from './Barre'

const duree = (s: number) => {
  const j = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (j) return `${j} j ${h} h`
  if (h) return `${h} h ${m} min`
  return `${m} min`
}

/** Sante de la machine. Volontairement separee des mesures de la serre :
 *  on ne surveille pas une carte comme on surveille une germination, et
 *  melanger les deux brouillerait la lecture. */
export default function Systeme() {
  const [etat, setEtat] = useState<EtatSysteme | null>(null)

  useEffect(() => {
    let vivant = true
    const lire = () =>
      lireSysteme()
        .then((e) => { if (vivant) setEtat(e) })
        .catch(() => undefined)
    lire()
    const t = setInterval(lire, 4000)
    return () => { vivant = false; clearInterval(t) }
  }, [])

  if (!etat) {
    return <p className="text-micro text-texte-faible">Lecture de l’état machine…</p>
  }

  const lignes = [
    {
      icone: LuCpu, libelle: 'Processeur',
      valeur: `${etat.charge_cpu} %`,
      detail: `${etat.coeurs} cœurs`,
      part: etat.charge_cpu,
    },
    {
      icone: LuMemoryStick, libelle: 'Mémoire',
      valeur: `${etat.memoire.part} %`,
      detail: `${etat.memoire.utilisee_go} / ${etat.memoire.totale_go} Go`,
      part: etat.memoire.part,
    },
    {
      icone: LuHardDrive, libelle: 'Stockage',
      valeur: `${etat.disque.part} %`,
      detail: `${etat.disque.utilise_go} / ${etat.disque.total_go} Go`,
      part: etat.disque.part,
    },
  ]

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-micro text-texte-doux">
        <span className="flex items-center gap-1.5">
          <LuClock size={13} className="text-texte-faible" />
          <span className="tabular-nums">{etat.horloge}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <LuThermometer size={13} className="text-texte-faible" />
          {etat.temperature_cpu !== null
            ? <span className="tabular-nums">{etat.temperature_cpu} °C</span>
            : <span className="text-texte-faible">n/d</span>}
        </span>
        <span className="text-texte-faible">en ligne {duree(etat.en_ligne_s)}</span>
      </div>

      <div className="flex flex-1 flex-col justify-center gap-3.5">
        {lignes.map(({ icone: Icone, libelle, valeur, detail, part }) => (
          <div key={libelle}>
            <div className="mb-1.5 flex items-center gap-2">
              <Icone size={14} className="shrink-0 text-texte-faible" />
              <span className="text-micro font-medium text-texte">{libelle}</span>
              <span className="ml-auto text-micro tabular-nums text-texte-doux">{valeur}</span>
            </div>
            <Barre part={part} />
            <p className="mt-1 text-[0.6rem] tabular-nums text-texte-faible">{detail}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
