from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from clone_wars.web.session import get_or_create_session

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_id = request.cookies.get("session_id")
    session_id, session = get_or_create_session(session_id)

    templates = request.app.state.templates
    response = templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
        },
    )
    response.set_cookie("session_id", session_id, httponly=True)
    return response
