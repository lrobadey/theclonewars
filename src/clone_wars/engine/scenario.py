from __future__ import annotations

from pathlib import Path

from war_sim.rules.scenario import load_game_state as _load_game_state
from war_sim.sim.state import GameState


def load_game_state(path: Path) -> GameState:
    return _load_game_state(path)
