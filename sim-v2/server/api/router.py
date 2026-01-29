from __future__ import annotations

from fastapi import APIRouter, Request, Response

from clone_wars.web.api import mappers, schemas
from server.session import get_or_create_session

router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/state", response_model=schemas.GameStateResponse)
async def get_state(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    async with session.lock:
        data = mappers.build_state_response(session.state)
    response.set_cookie("session_id", session_id, httponly=True)
    return data
