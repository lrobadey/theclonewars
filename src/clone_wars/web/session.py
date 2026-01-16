from __future__ import annotations

import uuid
from pathlib import Path

from clone_wars.engine.scenario import load_game_state
from clone_wars.web.models import WebSession

_sessions: dict[str, WebSession] = {}


def _load_initial_state():
    data_path = Path(__file__).resolve().parents[1] / "data" / "scenario.json"
    return load_game_state(data_path)


def get_or_create_session(session_id: str | None) -> tuple[str, WebSession]:
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    new_id = str(uuid.uuid4())
    state = _load_initial_state()
    session = WebSession(state=state)
    _sessions[new_id] = session
    return new_id, session


def get_session(session_id: str) -> WebSession | None:
    return _sessions.get(session_id)
