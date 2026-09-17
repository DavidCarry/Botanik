"""Prises de vue regulieres de la serre.

Pas un flux video : une image fixe, renouvelee a intervalle court. Un
MJPEG occuperait la carte et le reseau en continu pour montrer une
germination, qui bouge en heures et non en images par seconde. Une prise
par seconde donne le meme sentiment de direct pour une fraction du cout.

Deux choix de mise en oeuvre qui comptent :

  La camera reste OUVERTE entre deux prises. La rouvrir a chaque fois --
  ce que fait `rpicam-still` lance en boucle -- coute 480 ms par image
  contre 65 ms ici, soit la moitie d'un coeur au lieu d'un quinzieme.

  L'image est ecrite en MEMOIRE, dans /dev/shm, et non sur la carte SD.
  Soixante-dix kilo-octets par seconde feraient six gigaoctets par jour
  d'ecritures : la carte serait usee en quelques mois. Personne ne
  relit une image d'il y a une minute, elle n'a donc rien a faire sur un
  support permanent.

Ce service est le seul a tourner avec le PYTHON DU SYSTEME et non celui
du projet : `picamera2` s'appuie sur les liaisons libcamera, qui sont
installees par le systeme et ne s'installent pas avec pip.
"""

import os
import signal
import sys
import time

from config import CAMERA_FICHIER, CAMERA_S, CAMERA_TAILLE

# Delai avant la premiere prise : le reglage automatique de l'exposition
# et de la balance des blancs a besoin de quelques images pour se poser.
# Sans cela, la premiere vue est grise.
REGLAGE_S = 1.5

# Apres un echec, on attend avant de reessayer : une camera debranchee ne
# se rebranche pas en une seconde, et reessayer sans repit remplirait le
# journal plus vite que la serre ne pousse.
REPOS_ECHEC_S = 5.0


def capturer(camera, chemin: str) -> None:
    """Ecrit une image, sans jamais en laisser une a moitie ecrite.

    On passe par un fichier temporaire puis on renomme : `os.replace`
    est atomique, donc l'API sert toujours une image entiere -- soit
    l'ancienne, soit la nouvelle, jamais un melange des deux.
    """
    provisoire = f"{chemin}.part"
    camera.capture_file(provisoire, format="jpeg")
    os.replace(provisoire, chemin)


def main() -> int:
    from picamera2 import Picamera2

    os.makedirs(os.path.dirname(CAMERA_FICHIER), exist_ok=True)

    tourne = True

    def arreter(signum, frame):
        nonlocal tourne
        tourne = False

    signal.signal(signal.SIGINT, arreter)
    signal.signal(signal.SIGTERM, arreter)

    camera = Picamera2()
    camera.configure(camera.create_still_configuration(main={"size": CAMERA_TAILLE}))
    camera.start()

    # Mise au point continue. Le module ne la fait PAS de lui-meme : sans
    # cette ligne, l'objectif reste ou il etait et la serre sort floue.
    # Continue plutot qu'une passe unique, parce qu'on deplace la camera
    # et qu'on ouvre le chassis -- la scene change.
    try:
        from libcamera import controls
        camera.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        print("Mise au point continue activee", flush=True)
    except Exception as e:
        # Toutes les cameras n'ont pas d'autofocus : la v2 est a focale
        # fixe. Ce n'est pas une panne, juste une possibilite en moins.
        print(f"Pas de mise au point automatique : {e}", flush=True)

    time.sleep(REGLAGE_S)
    print(f"Camera ouverte, une prise toutes les {CAMERA_S}s "
          f"vers {CAMERA_FICHIER}", flush=True)

    plainte = None
    while tourne:
        depart = time.monotonic()
        try:
            capturer(camera, CAMERA_FICHIER)
            if plainte is not None:
                print("Camera de nouveau lisible", flush=True)
                plainte = None
            attente = CAMERA_S
        except Exception as e:
            # Se plaindre une fois, pas a chaque tour : une camera
            # debranchee noierait le journal en quelques minutes.
            if plainte != str(e):
                print(f"Prise de vue impossible : {e}", flush=True)
                plainte = str(e)
            attente = REPOS_ECHEC_S

        # Sommeil fractionne : un arret demande est pris en compte tout
        # de suite, et non a la fin de l'intervalle.
        fin = depart + attente
        while tourne and time.monotonic() < fin:
            time.sleep(min(0.2, max(0.0, fin - time.monotonic())))

    camera.stop()
    print("Camera arretee", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
