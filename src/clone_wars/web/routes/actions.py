from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from clone_wars.web.render.viewmodels import PANEL_SPECS
from clone_wars.web.session import get_or_create_session, reset_session

router = APIRouter()


@router.post("/action", response_class=HTMLResponse)
async def handle_action(request: Request):
    form = await request.form()
    action = form.get("action")
    if not action:
        return HTMLResponse("<p>Missing action.</p>", status_code=400)

    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    templates = request.app.state.templates

    async with session.lock:
        if action == "btn-reset":
            reset_session(session)
            session.controller.message = "SIMULATION RESET"
            session.controller.message_kind = "info"
            dirty_panels = set(PANEL_SPECS.keys())
        else:
            dirty_panels = session.controller.dispatch(action, dict(form), session.state)
        fragments = []
        for name in dirty_panels:
            spec = PANEL_SPECS.get(name)
            if spec is None:
                continue
            vm = spec.builder(session.state, session.controller)
            oob = name != "console"
            html = templates.get_template(spec.template).render({"vm": vm, "oob": oob})
            fragments.append(html)

    response = HTMLResponse("\n".join(fragments))
    response.set_cookie("session_id", session_id, httponly=True)
    return response
