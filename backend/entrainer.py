"""Entraine le reseau et range ses poids en base.

  python entrainer.py            entraine, evalue, enregistre
  python entrainer.py --essai    entraine et evalue sans rien enregistrer

Script et non service : on l'appelle quand on veut un nouveau modele. Le
service d'inference, lui, se contente de relire les poids.
"""

import sys
from datetime import datetime, timezone

import numpy as np
import psycopg

import donnees
import poids as magasin
import reseau
import seuils
from config import DB_URL

HYPERPARAMETRES = {"n_caches": 8, "taux": 0.5, "epoques": 4000, "graine": 0}


def matrice_confusion(vrai, prevu, n):
    m = np.zeros((n, n), dtype=int)
    for v, p in zip(vrai, prevu):
        m[v, p] += 1
    return m


def main():
    essai = "--essai" in sys.argv

    X, y = donnees.generer(6000, graine=0)
    Xa, ya, Xt, yt = donnees.separer(X, y, part_test=0.2, graine=0)
    b = donnees.bornes()
    Na, Nt = donnees.normaliser(Xa, b), donnees.normaliser(Xt, b)

    print(f"apprentissage {len(Xa)} exemples, test {len(Xt)}")
    p, histo = reseau.entrainer(Na, ya, **HYPERPARAMETRES, trace_tous=500)

    print("\nepoque    perte   exactitude")
    for e in histo:
        print(f"{e['epoque']:6}   {e['perte']:.4f}   {e['exactitude']:.4f}")

    # Le chiffre qui compte : des exemples jamais vus pendant la descente.
    exactitude_test = reseau.exactitude(p, Nt, yt)
    print(f"\nexactitude sur le jeu de TEST : {exactitude_test:.4f}")

    m = matrice_confusion(yt, reseau.predire(p, Nt), len(donnees.ACTIONS))
    print("\nmatrice de confusion (lignes = attendu, colonnes = predit)")
    print("            " + "".join(f"{a:>10}" for a in donnees.ACTIONS))
    for i, a in enumerate(donnees.ACTIONS):
        print(f"{a:>10}  " + "".join(f"{v:>10}" for v in m[i]))

    print("\nseuils appris, selon les conditions")
    for nom, t, l in [("nuit fraiche", 15, 0), ("journee douce", 21, 4000),
                      ("plein soleil", 30, 9000)]:
        f = seuils.frontieres(p, b, t, l)
        print(f"  {nom:15} {t:2.0f} C {l:5.0f} lux  ->  "
              f"arroser sous {f['bas']} %, ventiler au-dessus de {f['haut']} %")

    if essai:
        print("\n--essai : rien n'a ete enregistre")
        return

    meta = {
        "architecture": [len(donnees.ENTREES), HYPERPARAMETRES["n_caches"],
                         len(donnees.ACTIONS)],
        "entrees": donnees.ENTREES,
        "actions": donnees.ACTIONS,
        "bornes": b.tolist(),
        "hyperparametres": HYPERPARAMETRES,
        "exemples": {"apprentissage": len(Xa), "test": len(Xt)},
        "metriques": {"exactitude_test": round(exactitude_test, 4),
                      "perte_finale": histo[-1]["perte"]},
        "historique": histo,
    }
    version = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        magasin.enregistrer(conn, p, meta, version)
    print(f"\nmodele enregistre en base : {magasin.NOM} version {version}")


if __name__ == "__main__":
    main()
