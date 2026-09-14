"""Serveur de l'application Botanik.

Pour l'instant il ne fait qu'une chose : servir le frontend React compile.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

DIST = Path(__file__).parent.parent / "frontend" / "dist"

if not DIST.is_dir():
    raise RuntimeError(
        f"Frontend non compile : {DIST} est introuvable.\n"
        "Lance d'abord `npm run build` dans frontend/."
    )

app = FastAPI(title="Botanik")

# html=True fait servir index.html a la racine
app.mount("/", StaticFiles(directory=DIST, html=True), name="app")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
