"""Apprend a la serre a nommer des visages, a partir de photos.

    python apprendre_visages.py ~/references/*.jpg
    python apprendre_visages.py --liste
    python apprendre_visages.py --oublier armand

Le NOM DU FICHIER donne le nom de la personne : `armand.jpg` enregistre
une reference au nom d'« armand ». Plusieurs photos d'une meme personne
s'ajoutent les unes aux autres -- de face, de trois quarts -- et c'est la
meilleure des ressemblances qui decidera.

Ce qui est enregistre n'est pas la photo mais son empreinte : les 128
nombres que le modele tire du visage. Les fichiers d'origine peuvent etre
effaces ensuite, rien ne les relit.

Une photo par personne suffit, mais elle doit montrer UN visage, net et
de face. Le script dit ce qu'il a trouve et avec quelle confiance : si le
compte n'y est pas, c'est la photo qu'il faut reprendre.
"""

import os
import sys

import bdd
import empreintes
import schema
import visages
from config import VISAGES_SCORE_REFERENCE


def apprendre(regard, conn, fichier: str) -> bool:
    """Enregistre le plus grand visage d'une photo. Dit si ca a marche."""
    import cv2

    nom = os.path.splitext(os.path.basename(fichier))[0].strip().lower()
    image = cv2.imread(fichier)
    if image is None:
        print(f"  {nom:14} illisible : {fichier}")
        return False

    # Meme reduction que sur la vue en direct. Une photo de telephone
    # fait deux mille pixels de haut, et le detecteur y cherche des
    # visages qui occupent une FRACTION du cadre : sur un gros plan
    # pleine page, il n'en trouve aucun.
    reduite = regard.reduire(image)
    haut, large = reduite.shape[:2]
    regard.detecteur.setInputSize((large, haut))
    _, trouves = regard.detecteur.detect(reduite)

    if trouves is None or len(trouves) == 0:
        print(f"  {nom:14} aucun visage trouve — reprendre la photo, "
              f"de face et nette")
        return False
    if len(trouves) > 1:
        print(f"  {nom:14} {len(trouves)} visages sur la photo : "
              f"on garde le plus grand")

    visage = max(trouves, key=lambda v: v[2] * v[3])
    empreinte = regard.reconnaisseur.feature(
        regard.reconnaisseur.alignCrop(reduite, visage))
    empreintes.enregistrer(conn, nom, empreinte, os.path.basename(fichier))
    print(f"  {nom:14} appris — visage de {int(visage[2])}x{int(visage[3])} px, "
          f"confiance {visage[14]:.2f}")
    return True


def main(args: list[str]) -> int:
    if visages.cv2 is None:
        print("OpenCV absent : pip install opencv-python-headless")
        return 1

    with bdd.connexion() as conn:
        schema.preparer(conn)

        if "--liste" in args:
            connus = empreintes.inventaire(conn)
            if not connus:
                print("La serre ne connait personne.")
            for nom, combien in connus:
                print(f"  {nom:14} {combien} reference(s)")
            return 0

        if "--oublier" in args:
            qui = args[args.index("--oublier") + 1:]
            if not qui:
                print("--oublier attend un nom")
                return 1
            for nom in qui:
                efface = empreintes.retirer(conn, nom.strip().lower())
                print(f"  {nom:14} {efface} reference(s) effacee(s)")
            return 0

        fichiers = [a for a in args if not a.startswith("-")]
        if not fichiers:
            print(__doc__)
            return 1

        visages.cv2.setNumThreads(1)
        regard = visages.Regard(
            # Moins severe qu'en direct : c'est une photo choisie, et le
            # resultat s'affiche pour etre verifie.
            visages.cv2.FaceDetectorYN.create(
                visages.chemin(visages.VISAGES_MODELE), "", (640, 640),
                score_threshold=VISAGES_SCORE_REFERENCE),
            visages.reconnaisseur(),
        )
        if regard.reconnaisseur is None:
            print(f"Modele de reconnaissance absent : "
                  f"{visages.chemin(visages.VISAGES_SFACE)}")
            return 1

        print(f"{len(fichiers)} photo(s) a apprendre")
        reussites = sum(apprendre(regard, conn, f) for f in fichiers)
        print(f"\n{reussites}/{len(fichiers)} enregistrees")

        connus = empreintes.inventaire(conn)
        print("La serre connait : "
              + ", ".join(f"{n} ({c})" for n, c in connus))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
