from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from clone_wars.web.routes import actions, page, panels

WEB_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Clone Wars War Sim", lifespan=lifespan)

    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

    templates = Jinja2Templates(directory=WEB_DIR / "templates")
    app.state.templates = templates

    app.include_router(page.router)
    app.include_router(actions.router)
    app.include_router(panels.router)

    return app


app = create_app()
