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

import bdd
import empreintes
import service
from config import (
    CAMERA_FICHIER,
    CAMERA_TAILLE,
    TOPIC_VISAGES,
    VISAGES_LARGEUR,
    VISAGES_MEMOIRE_S,
    VISAGES_MODELE,
    VISAGES_RECONNAISSANCE_S,
    VISAGES_S,
    VISAGES_SCORE,
    VISAGES_SCORE_REFERENCE,
    VISAGES_SFACE,
    VISAGES_SIMILARITE,
    VISAGES_SUIVI,
)
# Le nom des inconnus est aussi un SUJET de regle : il vit donc avec le
# reste du vocabulaire des regles, pas ici.
from decision import ANONYME

try:
    import cv2
except ImportError:
    # Un message clair au demarrage vaut mieux qu'une trace d'import au
    # milieu du journal de systemd.
    cv2 = None

# Une image de serre ne contient pas dix personnes : une limite protege
# d'une detection qui s'emballerait sur un feuillage.
MAXIMUM = 8

# Relecture des references. Assez souvent pour qu'un visage tout juste
# appris soit reconnu presque tout de suite, assez rare pour ne pas
# interroger la base cinq fois par seconde.
RELECTURE_S = 10


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

    def __init__(self, detecteur, reconnaisseur=None):
        self.detecteur = detecteur
        # Absent, les visages sont encadres sans etre nommes : degrade,
        # pas casse.
        self.reconnaisseur = reconnaisseur
        self.lecture = drapeau_lecture()
        # Qui la serre sait nommer, relu de temps en temps.
        self.references: list = []
        self.prochaine_relecture = 0.0
        self.plainte: str | None = None
        # Les visages de l'image PRECEDENTE, avec leur nom : c'est ce qui
        # evite de redemander son identite a une tete qui n'a pas bouge.
        self.suivis: list[dict] = []
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

    def reduire(self, image):
        """L'image ramenee a la largeur de travail.

        Le decodage a deja fait le gros du chemin : il ne reste a
        redimensionner que si la camera ne tombe pas juste.
        """
        haut, large = image.shape[:2]
        if large <= VISAGES_LARGEUR:
            return image
        return cv2.resize(
            image, (VISAGES_LARGEUR, round(haut * VISAGES_LARGEUR / large)))

    def herite(self, cx: float, cy: float, pris: set) -> dict | None:
        """Le visage de l'image precedente qui se trouvait la.

        Sans ce rapprochement, chaque image reposerait la question « qui
        est-ce ? » a une tete qui n'a pas bouge -- soixante-quatre
        millisecondes, cinq fois par seconde, pour reapprendre ce qu'on
        savait deja.

        Un seul cadre precedent par cadre courant : deux personnes qui se
        croisent ne doivent pas se voir attribuer le meme nom.
        """
        meilleur, distance = None, VISAGES_SUIVI
        for i, s in enumerate(self.suivis):
            if i in pris:
                continue
            d = ((s["cx"] - cx) ** 2 + (s["cy"] - cy) ** 2) ** 0.5
            if d < distance:
                meilleur, distance = i, d
        if meilleur is None:
            return None
        pris.add(meilleur)
        return self.suivis[meilleur]

    def identifier(self, image, visage) -> str:
        """Le nom de ce visage, ou « Personne » s'il n'est pas connu.

        Le modele redresse d'abord la tete a partir des cinq reperes
        donnes par le detecteur -- yeux, nez, coins de la bouche -- puis
        la reduit a 128 nombres. Comparer deux visages, c'est comparer
        ces nombres.

        La MEILLEURE ressemblance l'emporte, et seulement si elle passe
        le seuil : en partant du seuil, un inconnu ne peut pas gagner par
        defaut.
        """
        if self.reconnaisseur is None or not self.references:
            return ANONYME
        try:
            empreinte = self.reconnaisseur.feature(
                self.reconnaisseur.alignCrop(image, visage))
        except cv2.error:
            # Visage au bord de l'image : le redressement sort du cadre.
            return ANONYME

        nom, ressemblance = ANONYME, VISAGES_SIMILARITE
        for candidat, reference in self.references:
            s = self.reconnaisseur.match(empreinte, reference,
                                         cv2.FaceRecognizerSF_FR_COSINE)
            if s > ressemblance:
                nom, ressemblance = candidat, s
        return nom

    def regarder(self, image, maintenant: float) -> list[dict]:
        """Les visages d'une image, nommes, en coordonnees de 0 a 1."""
        image = self.reduire(image)
        rh, rl = image.shape[:2]
        self.detecteur.setInputSize((rl, rh))
        _, trouves = self.detecteur.detect(image)
        if trouves is None:
            self.suivis = []
            return []

        # Chaque ligne donne le cadre, puis cinq reperes du visage, et
        # son score en dernier.
        visages, suivis, pris = [], [], set()
        for v in trouves[:MAXIMUM]:
            x, y, l, h = (float(n) for n in v[:4])
            cx, cy = (x + l / 2) / rl, (y + h / 2) / rh

            precedent = self.herite(cx, cy, pris)
            nom = precedent["nom"] if precedent else ANONYME
            identifie_a = precedent["identifie_a"] if precedent else 0.0
            # Un visage qui arrive est identifie tout de suite ; celui
            # qui reste l'est de temps en temps, au cas ou la premiere
            # lecture serait tombee sur un mauvais angle.
            if maintenant - identifie_a > VISAGES_RECONNAISSANCE_S:
                nom = self.identifier(image, v)
                identifie_a = maintenant

            suivis.append({"cx": cx, "cy": cy, "nom": nom,
                           "identifie_a": identifie_a})
            visages.append({
                "x": round(max(0.0, x / rl), 4),
                "y": round(max(0.0, y / rh), 4),
                "l": round(min(1.0, l / rl), 4),
                "h": round(min(1.0, h / rh), 4),
                "nom": nom,
                "score": round(float(v[14]), 3),
            })

        self.suivis = suivis
        return visages

    def relire_references(self) -> None:
        """Relit qui la serre sait nommer.

        Periodiquement, et non une fois pour toutes : une reference
        ajoutee doit prendre effet sans redemarrer le service.

        Une base injoignable ne fait rien perdre -- on garde la liste
        precedente. Oublier les noms parce que la base tousse serait pire
        que de les garder un peu trop longtemps.
        """
        try:
            with bdd.connexion() as conn:
                references = empreintes.lire(conn)
        except Exception as e:
            if self.plainte != str(e):
                print(f"References illisibles : {e}", flush=True)
                self.plainte = str(e)
            return

        self.plainte = None
        if len(references) != len(self.references):
            noms = sorted({nom for nom, _ in references})
            print(f"{len(references)} reference(s) : "
                  f"{', '.join(noms) or 'aucune'}", flush=True)
        self.references = references

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

        if maintenant >= self.prochaine_relecture:
            self.relire_references()
            self.prochaine_relecture = maintenant + RELECTURE_S

        try:
            datee = os.path.getmtime(CAMERA_FICHIER)
        except OSError:
            datee = 0.0        # camera arretee, ou pas encore demarree

        nouvelle = bool(datee) and datee != self.image_datee
        if nouvelle:
            self.image_datee = datee
            image = cv2.imread(CAMERA_FICHIER, self.lecture)
            if image is not None:
                trouves = self.regarder(image, maintenant)
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


def chemin(modele: str) -> str:
    """Le chemin d'un modele, relatif au dossier du backend."""
    if os.path.isabs(modele):
        return modele
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), modele)


def detecteur():
    """Celui qui trouve les visages. Sans lui, il n'y a rien a faire.

    La taille donnee ici est redefinie a chaque image par
    `setInputSize` : le constructeur l'exige, mais elle ne sert a rien.
    """
    return cv2.FaceDetectorYN.create(
        chemin(VISAGES_MODELE), "", (VISAGES_LARGEUR, VISAGES_LARGEUR),
        score_threshold=VISAGES_SCORE,
    )


def reconnaisseur():
    """Celui qui les nomme, ou None s'il n'est pas installe.

    Ses 37 Mo ne sont pas dans le depot : sans eux, la serre encadre les
    visages sans les nommer, ce qui reste utilisable.
    """
    voie = chemin(VISAGES_SFACE)
    return cv2.FaceRecognizerSF.create(voie, "") if os.path.exists(voie) else None


def regard_de_reference():
    """Un regard regle pour APPRENDRE, et non pour surveiller.

    Son detecteur est moins severe qu'en direct, et c'est voulu : une
    reference est une photo choisie, dont le resultat est annonce pour
    etre verifie. En direct, la meme indulgence encadrerait une plante
    toutes les deux secondes.
    """
    return Regard(
        cv2.FaceDetectorYN.create(
            chemin(VISAGES_MODELE), "", (VISAGES_LARGEUR, VISAGES_LARGEUR),
            score_threshold=VISAGES_SCORE_REFERENCE),
        reconnaisseur(),
    )


def apprendre(regard, conn, nom: str, image, origine: str) -> dict:
    """Enregistre le plus grand visage d'une image comme reference de `nom`.

    Le coeur de l'apprentissage, et le seul : le script en ligne de
    commande et la route de l'API passent tous les deux par ici. Deux
    copies de cette suite d'appels finiraient par differer, et l'une des
    deux produirait des empreintes que l'autre ne reconnaitrait pas.

    Leve `ValueError` quand la photo ne convient pas, avec de quoi le
    dire a celui qui l'a fournie : c'est presque toujours la photo qu'il
    faut reprendre, pas un reglage qu'il faut changer.
    """
    if regard.reconnaisseur is None:
        raise ValueError("modèle de reconnaissance absent sur la serre")

    # Meme reduction que sur la vue en direct. Une photo de telephone
    # fait deux mille pixels de haut, et le detecteur y cherche des
    # visages qui occupent une FRACTION du cadre : sur un gros plan
    # pleine page, il n'en trouve aucun.
    reduite = regard.reduire(image)
    haut, large = reduite.shape[:2]
    regard.detecteur.setInputSize((large, haut))
    _, trouves = regard.detecteur.detect(reduite)

    if trouves is None or len(trouves) == 0:
        raise ValueError("aucun visage trouvé — reprendre la photo, "
                         "de face et nette")

    # Le plus grand, et non le mieux note : sur une photo de groupe, c'est
    # celui qui pose qui est au premier plan.
    visage = max(trouves, key=lambda v: v[2] * v[3])
    try:
        empreinte = regard.reconnaisseur.feature(
            regard.reconnaisseur.alignCrop(reduite, visage))
    except cv2.error as e:
        # Visage trop au bord : le redressement sort du cadre.
        raise ValueError("visage trop près du bord — recadrer la photo") from e

    empreintes.enregistrer(conn, nom, empreinte, origine)
    return {
        "nom": nom,
        "largeur": int(visage[2]),
        "hauteur": int(visage[3]),
        "confiance": round(float(visage[14]), 2),
        # Les visages qu'on a laisses de cote, pour que l'ecran puisse le
        # dire : une reference prise sur la mauvaise tete d'une photo de
        # groupe est une erreur qu'on ne voit pas autrement.
        "ecartes": len(trouves) - 1,
    }


def main() -> int:
    if cv2 is None:
        print("OpenCV absent : pip install opencv-python-headless", flush=True)
        return 1

    if not os.path.exists(chemin(VISAGES_MODELE)):
        print(f"Modele introuvable : {chemin(VISAGES_MODELE)}", flush=True)
        return 1

    # UN SEUL fil. Laisse a lui-meme, OpenCV etale la detection sur les
    # quatre coeurs : 30 ms au lieu de 42, mais pres du double de temps
    # processeur, pris aux services qui mesurent et qui decident. Un
    # agrement n'a pas a reveiller toute la machine dix fois par seconde
    # pour gagner douze millisecondes que personne ne verra.
    cv2.setNumThreads(1)

    nommeur = reconnaisseur()
    regard = Regard(detecteur(), nommeur)

    print(f"Visages : lecture de {CAMERA_FICHIER} toutes les {VISAGES_S}s",
          flush=True)
    print("  reconnaissance active" if nommeur else
          "  sans reconnaissance : modele absent, tout le monde reste "
          f"« {ANONYME} »", flush=True)
    service.executer("Visages", periode=VISAGES_S, travail=regard.tour)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
