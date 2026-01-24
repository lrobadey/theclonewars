from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from clone_wars.web.routes import actions, page, panels

WEB_DIR = Path(__file__).parent


class _NoCacheDevMiddleware(BaseHTTPMiddleware):
    """Disable client-side caching for the dev server.

    This prevents stale HTMX panel HTML and static assets (CSS) from sticking around
    when iterating quickly on UI tweaks.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # Keep this intentionally broad for local dev ergonomics.
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Clone Wars War Sim", lifespan=lifespan)

    # Dev UX: make refreshes reliable (esp. with HTMX partials + browser caches).
    app.add_middleware(_NoCacheDevMiddleware)

    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")

    templates = Jinja2Templates(directory=WEB_DIR / "templates")
    app.state.templates = templates

    app.include_router(page.router)
    app.include_router(actions.router)
    app.include_router(panels.router)

    return app


app = create_app()
