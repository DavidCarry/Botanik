/** Maquette de la serre, en trois dimensions.
 *
 *  Reproduit le chassis reel : un cadre de bois, des parois vitrees, un
 *  couvercle releve sur sa charniere arriere, et de la terre semee de
 *  lentilles. Tout est en CSS -- six plans et des transformations.
 *
 *  Les pousses sont tirees une fois pour toutes a l'ecriture, et non au
 *  hasard : une maquette qui change de disposition a chaque affichage
 *  donnerait l'impression d'un bug plutot que d'un jardin.
 */
const POUSSES = [
  { x: 18, z: 26, biais: -18, taille: 1.0 },
  { x: 31, z: 62, biais: 34, taille: 0.85 },
  { x: 44, z: 34, biais: -62, taille: 1.1 },
  { x: 57, z: 71, biais: 12, taille: 0.9 },
  { x: 69, z: 40, biais: 78, taille: 1.05 },
  { x: 80, z: 66, biais: -40, taille: 0.8 },
  { x: 26, z: 48, biais: 58, taille: 0.95 },
  { x: 63, z: 22, biais: -8, taille: 0.75 },
  { x: 88, z: 33, biais: 24, taille: 0.9 },
  { x: 11, z: 58, biais: -74, taille: 0.85 },
];

export default function Serre() {
  return (
    <div className="h-full w-full" style={{ containerType: "size" }}>
      <div className="serre grid h-full w-full place-items-center overflow-hidden">
        <div className="scene">
          {/* Le fond et les cotes d'abord : le navigateur trie lui-meme les
            plans selon leur profondeur, mais l'ordre du balisage depart
            les egalites. */}
          <div className="arriere vitre" />
          <div className="gauche vitre" />
          <div className="droite vitre" />

          <div className="terreau">
            {POUSSES.map((p, i) => (
              <span
                key={i}
                className="pousse"
                style={
                  {
                    left: `${p.x}%`,
                    top: `${p.z}%`,
                    scale: p.taille,
                    "--biais": `${p.biais}deg`,
                  } as React.CSSProperties
                }
              >
                <span className="tige" />
                <span className="feuille g" />
                <span className="feuille d" />
              </span>
            ))}
          </div>

          <div className="avant vitre" />
          <div className="couvercle vitre" />
        </div>
      </div>
    </div>
  );
}
