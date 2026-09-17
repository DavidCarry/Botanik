"""Entraine le reseau et range ses poids en base.

  python entrainer.py            entraine, evalue, enregistre
  python entrainer.py --essai    entraine et evalue sans rien enregistrer

Script et non service : on l'appelle quand on veut un nouveau modele. Le
service d'inference, lui, se contente de relire les poids.
"""

import sys
from datetime import datetime, timezone

import bdd
import donnees
import poids as magasin
import reseau
import seuils
from decision import GRANDEURS

# Dix jugements se partagent la meme couche cachee. A quatorze neurones,
# les frontieres etroites -- « trop de lumiere », qui ne couvre qu'un
# douzieme de l'echelle -- restaient molles : la probabilite franchissait
# 0,5 de justesse, et le seuil devenait sensible au contexte. Vingt
# neurones laissent de quoi les representer toutes.
HYPERPARAMETRES = {"n_caches": 20, "taux": 1.5, "epoques": 14000, "graine": 0}

# Conditions sous lesquelles on montre les seuils appris, pour verifier
# d'un coup d'oeil qu'ils se deplacent comme ils le doivent.
SITUATIONS = [
    ("nuit fraiche", {"temperature_air": 14, "luminosite": 0, "heure": 3,
                      "eclairement_jour": 0, "niveau_eau": 80}),
    ("matinee douce", {"temperature_air": 20, "luminosite": 33, "heure": 9,
                       "eclairement_jour": 2, "niveau_eau": 80}),
    ("plein soleil", {"temperature_air": 30, "luminosite": 83, "heure": 14,
                      "eclairement_jour": 7, "niveau_eau": 80}),
]



def main():
    essai = "--essai" in sys.argv

    X, Y = donnees.generer(9000, graine=0)
    Xa, Ya, Xt, Yt = donnees.separer(X, Y, part_test=0.2, graine=0)
    b = donnees.bornes()
    Na, Nt = donnees.normaliser(Xa, b), donnees.normaliser(Xt, b)

    print(f"apprentissage {len(Xa)} exemples, test {len(Xt)}, "
          f"{len(donnees.ENTREES)} entrees -> {len(donnees.SORTIES)} jugements")
    p, histo = reseau.entrainer(Na, Ya, **HYPERPARAMETRES, trace_tous=1000)

    print("\nepoque    perte   exactitude")
    for e in histo:
        print(f"{e['epoque']:6}   {e['perte']:.4f}   {e['exactitude']:.4f}")

    # Les chiffres qui comptent : des exemples jamais vus pendant la descente.
    par_sortie = reseau.exactitude(p, Nt, Yt)
    tout_juste = reseau.exactitude_complete(p, Nt, Yt)
    print(f"\nsur le jeu de TEST : {par_sortie:.4f} par jugement, "
          f"{tout_juste:.4f} sur les dix a la fois")

    print("\ndetail par jugement (test)")
    prevu = reseau.predire(p, Nt)
    detail = {}
    for i, nom in enumerate(donnees.SORTIES):
        juste = float((prevu[:, i] == (Yt[:, i] >= 0.5)).mean())
        detail[nom] = round(juste, 4)
        print(f"  {nom:26} {juste:.4f}   (positif {Yt[:, i].mean() * 100:4.1f} %)")

    print("\nseuils appris, selon les conditions")
    for nom, contexte in SITUATIONS:
        f = seuils.frontieres(p, b, contexte)
        print(f"  {nom}")
        for grandeur, s in f.items():
            print(f"    {grandeur:20} bas {str(s['bas']):>8}   haut {str(s['haut']):>8}")

    if essai:
        print("\n--essai : rien n'a ete enregistre")
        return

    meta = {
        "architecture": [len(donnees.ENTREES), HYPERPARAMETRES["n_caches"],
                         len(donnees.SORTIES)],
        "entrees": donnees.ENTREES,
        "sorties": donnees.SORTIES,
        "grandeurs": list(GRANDEURS),
        "bornes": b.tolist(),
        "hyperparametres": HYPERPARAMETRES,
        "exemples": {"apprentissage": len(Xa), "test": len(Xt)},
        "metriques": {"exactitude_test": round(par_sortie, 4),
                      "exactitude_complete": round(tout_juste, 4),
                      "perte_finale": histo[-1]["perte"],
                      "par_jugement": detail},
        "historique": histo,
    }
    version = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    with bdd.connexion() as conn:
        magasin.enregistrer(conn, p, meta, version)
    print(f"\nmodele enregistre en base : {magasin.NOM} version {version}")


if __name__ == "__main__":
    main()
