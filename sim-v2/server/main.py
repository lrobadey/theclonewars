from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from server.api import router as api_router

SERVER_DIR = Path(__file__).resolve().parent
SIM_V2_ROOT = SERVER_DIR.parent
CLIENT_DIST = SIM_V2_ROOT / "client" / "dist"
ASSETS_DIR = CLIENT_DIST / "assets"
INDEX_FILE = CLIENT_DIST / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Schism Sim (v2)", lifespan=lifespan)

    app.include_router(api_router)

    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        if INDEX_FILE.exists():
            return FileResponse(INDEX_FILE)
        return HTMLResponse(
            "<h1>React build missing</h1>\n"
            "<p>Run <code>npm install</code> and <code>npm run build</code> in sim-v2/client.</p>",
            status_code=501,
        )

    return app


app = create_app()
