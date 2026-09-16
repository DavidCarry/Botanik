/** Presentation du projet, sur un fond vegetal.
 *
 *  Le fond est dessine, non photographie : des feuilles en SVG dans les
 *  verts du site. Une photo libre de droits aurait apporte ses propres
 *  couleurs et sa propre lumiere, et jure avec le reste.
 */
const FEUILLES = [
  { x: 8, y: 62, t: -18, e: 1.5, o: 0.26 },
  { x: 22, y: 82, t: 24, e: 1.1, o: 0.2 },
  { x: 38, y: 55, t: -8, e: 1.8, o: 0.17 },
  { x: 58, y: 78, t: 32, e: 1.3, o: 0.22 },
  { x: 74, y: 58, t: -28, e: 1.6, o: 0.18 },
  { x: 90, y: 80, t: 14, e: 1.2, o: 0.21 },
  { x: 48, y: 92, t: -40, e: 1.4, o: 0.17 },
]

export default function Projet() {
  return (
    <div className="relative h-full w-full overflow-hidden rounded-carte border border-bordure">
      <svg
        aria-hidden
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMax slice"
        className="absolute inset-0 size-full"
      >
        <defs>
          <linearGradient id="feuillage" x1="0" y1="0" x2="0.4" y2="1">
            <stop offset="0%" stopColor="var(--p-lime-400)" />
            <stop offset="100%" stopColor="var(--p-vert-700)" />
          </linearGradient>
        </defs>

        {FEUILLES.map((f, i) => (
          <path
            key={i}
            // Une feuille : deux arcs opposes qui se rejoignent en pointe.
            d="M 0 0 C 9 -5 18 -2 22 6 C 15 13 5 11 0 0 Z"
            fill="url(#feuillage)"
            opacity={f.o}
            transform={`translate(${f.x} ${f.y}) rotate(${f.t}) scale(${f.e})`}
          />
        ))}
      </svg>

      {/* Le texte doit rester lisible quoi qu'il y ait derriere. */}
      <span
        aria-hidden
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(105deg, rgba(2,8,5,0.82) 0%, rgba(2,8,5,0.62) 55%, rgba(2,8,5,0.35) 100%)',
        }}
      />

      <div className="relative flex h-full flex-col justify-center gap-2.5 px-5 py-4 sm:px-7">
        <h3 className="text-menu font-semibold tracking-tight text-texte">
          Une serre qui décide elle-même
        </h3>
        <p className="max-w-[46ch] text-micro leading-relaxed text-texte-doux">
          Quatre sondes mesurent l’ambiance de germination de lentilles —
          humidité du sol, température, lumière, réserve d’eau. Les mesures
          circulent sur un broker <span className="text-texte">MQTT</span>,
          sont archivées dans <span className="text-texte">PostgreSQL</span>,
          et remontent à l’écran en direct.
        </p>
        <p className="max-w-[46ch] text-micro leading-relaxed text-texte-doux">
          Un réseau de neurones écrit à la main, entraîné sur un jeu de données
          construit pour l’occasion, décide de l’arrosage et de la ventilation.
          Il ne reçoit aucun seuil : il les a appris, et les déplace selon la
          chaleur et la lumière.
        </p>
        <p className="text-[0.6rem] text-texte-faible">
          Raspberry Pi 5 · Mosquitto · FastAPI · React · NumPy
        </p>
      </div>
    </div>
  )
}
