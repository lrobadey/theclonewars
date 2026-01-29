from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from clone_wars.web.api import router as api_router

WEB_DIR = Path(__file__).parent
FRONTEND_DIR = WEB_DIR.parent / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
ASSETS_DIR = DIST_DIR / "assets"
INDEX_FILE = DIST_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Clone Wars War Sim (React)", lifespan=lifespan)

    app.include_router(api_router)

    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        if INDEX_FILE.exists():
            return FileResponse(INDEX_FILE)
        return HTMLResponse(
            "<h1>React build missing</h1>\n"
            "<p>Run <code>npm install</code> and <code>npm run build</code> in src/clone_wars/frontend.</p>",
            status_code=501,
        )

    return app


app = create_app()
