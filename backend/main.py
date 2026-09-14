"""Serveur de l'application Botanik.

Expose l'etat des capteurs et sert le frontend compile.

ATTENTION a l'ordre des declarations : le montage des fichiers statiques se
fait sur "/" et intercepte donc tout. Les routes /api doivent imperativement
etre declarees AVANT, sinon elles ne sont jamais atteintes.
"""

from pathlib import Path

import psycopg
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from config import DB_URL

RACINE = Path(__file__).parent
DIST = RACINE.parent / "frontend" / "dist"
REGISTRE = RACINE / "capteurs.yaml"

# Derniere valeur connue de chaque capteur, en une seule requete.
DERNIERES = """
    SELECT DISTINCT ON (capteur) capteur, valeur, unite, ts
    FROM mesures
    ORDER BY capteur, ts DESC
"""

app = FastAPI(title="Botanik")


def capteurs_actifs():
    with open(REGISTRE, encoding="utf-8") as f:
        declares = yaml.safe_load(f)["capteurs"]
    return [c for c in declares if c.get("actif", False)]


@app.get("/api/capteurs")
def capteurs():
    """Les capteurs actifs, chacun avec sa derniere mesure si elle existe."""
    try:
        with psycopg.connect(DB_URL, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(DERNIERES)
                dernieres = {
                    capteur: {"valeur": valeur, "unite": unite, "ts": ts.isoformat()}
                    for capteur, valeur, unite, ts in cur.fetchall()
                }
    except psycopg.Error as e:
        raise HTTPException(503, f"base de donnees injoignable : {e}") from e

    return [
        {
            "id": c["id"],
            "libelle": c["libelle"],
            "unite": c["unite"],
            "ideal": c["ideal"],
            "echelle": c["echelle"],
            # None tant qu'aucune mesure n'est arrivee pour ce capteur
            "mesure": dernieres.get(c["id"]),
        }
        for c in capteurs_actifs()
    ]


# ---- le montage doit rester en dernier ----
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="app")
else:
    # Pas bloquant : en developpement le front est servi par Vite sur :5173,
    # et l'API doit pouvoir tourner seule.
    print(f"Frontend non compile ({DIST}) -- seules les routes /api repondent")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
