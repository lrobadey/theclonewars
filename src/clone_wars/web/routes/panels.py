from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from clone_wars.web.render.viewmodels import PANEL_SPECS
from clone_wars.web.session import get_or_create_session

router = APIRouter()


@router.get("/panel/{name}", response_class=HTMLResponse)
async def panel(request: Request, name: str):
    spec = PANEL_SPECS.get(name)
    if spec is None:
        return HTMLResponse("<p>Panel not found.</p>", status_code=404)

    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    templates = request.app.state.templates

    async with session.lock:
        session.controller.sync_with_state(session.state)
        vm = spec.builder(session.state, session.controller)
        html = templates.get_template(spec.template).render({"vm": vm, "oob": False})

    response = HTMLResponse(html)
    response.set_cookie("session_id", session_id, httponly=True)
    return response
