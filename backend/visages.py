"""Qui se trouve devant la serre.

Lit la derniere vue de la camera, y cherche des visages, et publie leur
position. Rien de plus : c'est l'interface qui dessine les cadres, et
l'image servie aux navigateurs n'est jamais retouchee.

Ce partage a une raison. Graver les cadres dans le JPEG obligerait la
Pi a decoder puis reencoder dix images par seconde, pour un trait
pixelise et un texte a la police d'OpenCV. En publiant des nombres, on
laisse le navigateur dessiner -- net a toutes les tailles, aux couleurs
du tableau de bord, et sans une image reencodee.

Les positions sont RELATIVES a l'image, de 0 a 1. L'interface affiche la
vue tantot en vignette, tantot en plein ecran, rognee dans les deux cas :
des pixels l'obligeraient a connaitre la resolution de la camera.

Le detecteur est YuNet, un modele PRE-ENTRAINE livre avec OpenCV. Il n'a
rien a voir avec le reseau de jugement de la serre, qui est ecrit a la
main dans `reseau.py` : celui-ci sait dire ou est un visage, et rien
d'autre.

Ce service est un agrement. S'il s'arrete, la vue reste et personne
d'autre ne s'en apercoit -- aucune decision de la serre n'en depend.
"""

import json
import os
import time

import service
from config import (
    CAMERA_FICHIER,
    CAMERA_TAILLE,
    TOPIC_VISAGES,
    VISAGES_LARGEUR,
    VISAGES_MEMOIRE_S,
    VISAGES_MODELE,
    VISAGES_S,
    VISAGES_SCORE,
)

try:
    import cv2
except ImportError:
    # Un message clair au demarrage vaut mieux qu'une trace d'import au
    # milieu du journal de systemd.
    cv2 = None

# Tant qu'aucune reference n'a ete enregistree, tout le monde porte ce
# nom. Le jour ou on apprendra des visages a la serre, il ne restera
# qu'aux inconnus.
ANONYME = "Personne"

# Une image de serre ne contient pas dix personnes : une limite protege
# d'une detection qui s'emballerait sur un feuillage.
MAXIMUM = 8


def drapeau_lecture() -> int:
    """Comment decoder le JPEG : deja reduit, si possible.

    Le decodeur sait rendre directement une image de moitie, de quart ou
    de huitieme, pour une fraction du travail. Decoder 1280 de large
    pour reduire ensuite a 640 revenait a payer deux fois le meme
    pixel -- et c'etait la moitie du cout de ce service.

    On prend la plus petite reduction qui reste au-dessus de la largeur
    de travail ; `regarder` se charge du reste s'il en reste.
    """
    for facteur, drapeau in ((8, cv2.IMREAD_REDUCED_COLOR_8),
                             (4, cv2.IMREAD_REDUCED_COLOR_4),
                             (2, cv2.IMREAD_REDUCED_COLOR_2)):
        if CAMERA_TAILLE[0] / facteur >= VISAGES_LARGEUR:
            return drapeau
    return cv2.IMREAD_COLOR


class Regard:
    """Le detecteur, et ce qu'il a vu en dernier."""

    def __init__(self, detecteur):
        self.detecteur = detecteur
        self.lecture = drapeau_lecture()
        # Les visages affiches en ce moment, et l'instant ou on en a
        # reellement vu pour la derniere fois.
        self.vus: list[dict] = []
        self.vus_a = 0.0
        # Date de l'image deja examinee : inutile de refaire le meme
        # travail sur une vue que la camera n'a pas renouvelee.
        self.image_datee = 0.0
        # Ce qui est deja parti, pour se taire quand rien ne change :
        # une serre vide n'a aucune raison d'occuper le broker dix fois
        # par seconde.
        self.publie: list[dict] | None = None

    def regarder(self, image) -> list[dict]:
        """Les visages d'une image, en coordonnees de 0 a 1."""
        haut, large = image.shape[:2]
        # Le decodage a deja fait le gros du chemin : il ne reste a
        # redimensionner que si la camera ne tombe pas juste.
        if large > VISAGES_LARGEUR:
            image = cv2.resize(
                image, (VISAGES_LARGEUR, round(haut * VISAGES_LARGEUR / large)))

        rh, rl = image.shape[:2]
        self.detecteur.setInputSize((rl, rh))
        _, trouves = self.detecteur.detect(image)
        if trouves is None:
            return []

        # Chaque ligne donne le cadre, puis cinq reperes du visage --
        # yeux, nez, coins de la bouche -- et son score en dernier. Seuls
        # le cadre et le score nous servent ; les reperes attendront la
        # reconnaissance, qui s'en sert pour redresser le visage.
        visages = []
        for v in trouves[:MAXIMUM]:
            x, y, l, h = (float(n) for n in v[:4])
            visages.append({
                "x": round(max(0.0, x / rl), 4),
                "y": round(max(0.0, y / rh), 4),
                "l": round(min(1.0, l / rl), 4),
                "h": round(min(1.0, h / rh), 4),
                "nom": ANONYME,
                "score": round(float(v[14]), 3),
            })
        return visages

    def oublier(self, maintenant: float) -> bool:
        """Vrai quand plus rien n'a ete vu depuis assez longtemps.

        Un visage perdu une image ou deux -- un clignement, un profil,
        un passage dans l'ombre -- reste affiche un court instant. Sans
        ce delai le cadre papillote, ce qui se remarque bien plus qu'un
        leger retard a l'effacement.
        """
        return maintenant - self.vus_a > VISAGES_MEMOIRE_S

    def tour(self, client) -> None:
        maintenant = time.monotonic()
        try:
            datee = os.path.getmtime(CAMERA_FICHIER)
        except OSError:
            datee = 0.0        # camera arretee, ou pas encore demarree

        nouvelle = bool(datee) and datee != self.image_datee
        if nouvelle:
            self.image_datee = datee
            image = cv2.imread(CAMERA_FICHIER, self.lecture)
            if image is not None:
                trouves = self.regarder(image)
                if trouves:
                    self.vus = trouves
                    self.vus_a = maintenant
                elif self.oublier(maintenant):
                    self.vus = []
        elif self.oublier(maintenant):
            # La camera s'est tue : ses derniers visages ne valent plus
            # rien, et les laisser donnerait une vue figee avec des
            # cadres qui ne bougent plus.
            self.vus = []

        self.annoncer(client)

    def annoncer(self, client) -> None:
        """Publie a chaque image, sauf quand il n'y a personne.

        Se taire des que rien ne CHANGE serait plus economique, mais un
        navigateur ouvert pendant qu'une personne se tient immobile
        n'aurait alors jamais son cadre : le flux ne pousse que ce qui
        arrive apres la connexion, et rien n'arriverait plus.

        On republie donc tant qu'il y a quelqu'un -- dix petits messages
        par seconde, le temps du passage -- et on se tait des que la vue
        est vide, ce qui est l'immense majorite du temps.

        Message RETENU : au demarrage de l'API, le broker lui redonne
        immediatement le dernier etat connu.
        """
        # `publie` vaut None tant qu'on n'a rien dit : le tout premier
        # tour annonce donc une vue vide, ce qui efface le message retenu
        # d'une execution precedente. Sans cela, un redemarrage laisserait
        # sur le broker des visages partis depuis longtemps.
        if not self.vus and self.publie == []:
            return
        self.publie = self.vus
        client.publish(TOPIC_VISAGES, json.dumps({"visages": self.vus}),
                       qos=0, retain=True)


def modele() -> str:
    """Le chemin du detecteur, relatif au dossier du backend."""
    if os.path.isabs(VISAGES_MODELE):
        return VISAGES_MODELE
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        VISAGES_MODELE)


def main() -> int:
    if cv2 is None:
        print("OpenCV absent : pip install opencv-python-headless", flush=True)
        return 1

    chemin = modele()
    if not os.path.exists(chemin):
        print(f"Modele introuvable : {chemin}", flush=True)
        return 1

    # UN SEUL fil. Laisse a lui-meme, OpenCV etale la detection sur les
    # quatre coeurs : 30 ms au lieu de 42, mais pres du double de temps
    # processeur, pris aux services qui mesurent et qui decident. Un
    # agrement n'a pas a reveiller toute la machine dix fois par seconde
    # pour gagner douze millisecondes que personne ne verra.
    cv2.setNumThreads(1)

    # La taille donnee ici est redefinie a chaque image par
    # `setInputSize` : le constructeur l'exige, mais elle ne sert a rien.
    detecteur = cv2.FaceDetectorYN.create(
        chemin, "", (VISAGES_LARGEUR, VISAGES_LARGEUR),
        score_threshold=VISAGES_SCORE,
    )

    print(f"Visages : {os.path.basename(chemin)} sur {CAMERA_FICHIER}, "
          f"toutes les {VISAGES_S}s", flush=True)
    service.executer("Visages", periode=VISAGES_S, travail=Regard(detecteur).tour)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
