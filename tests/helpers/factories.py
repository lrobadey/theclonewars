from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable

from war_sim.sim.state import GameState
from war_sim.rules.scenario import load_game_state


def _default_scenario_path() -> Path:
    return Path(__file__).resolve().parents[2] / "sim-v2" / "data" / "scenarios" / "default.json"


def make_state(
    *,
    seed: int = 1,
    scenario_path: Path | None = None,
    apply: Callable[[GameState], None] | None = None,
) -> GameState:
    """Create a fresh GameState for tests, with optional in-place overrides."""
    path = scenario_path or _default_scenario_path()
    state = load_game_state(path)
    state.rng_seed = seed
    if apply is not None:
        apply(state)
    return state


def clone_state(state: GameState) -> GameState:
    """Best-effort clone for tests; prefer make_state when possible."""
    return replace(state)
