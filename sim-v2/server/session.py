from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from clone_wars.engine.scenario import load_game_state
from clone_wars.engine.state import GameState

# Resolve sim-v2/data relative to this package (server/ is inside sim-v2/)
_SIM_V2_ROOT = Path(__file__).resolve().parents[1]
_DATA_DIR = _SIM_V2_ROOT / "data"
_SCENARIO_PATH = _DATA_DIR / "scenario.json"


@dataclass
class V2Session:
    state: GameState
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def reset(self, state: GameState) -> None:
        self.state = state


_sessions: dict[str, V2Session] = {}


def _load_initial_state() -> GameState:
    return load_game_state(_SCENARIO_PATH)


def reset_session(session: V2Session) -> None:
    session.reset(_load_initial_state())


def get_or_create_session(session_id: str | None) -> tuple[str, V2Session]:
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    new_id = str(uuid.uuid4())
    state = _load_initial_state()
    session = V2Session(state=state)
    _sessions[new_id] = session
    return new_id, session


def get_session(session_id: str) -> V2Session | None:
    return _sessions.get(session_id)
