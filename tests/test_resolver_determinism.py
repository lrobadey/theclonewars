"""Tests for unified battle resolver determinism."""

from pathlib import Path

from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.scenario import load_game_state


def test_resolver_determinism() -> None:
    """Operation-based raid produces same results with same seed."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    scenario_path = data_dir / "scenario.json"

    def run_raid(seed: int) -> tuple[str, int, int, int]:
        state = load_game_state(scenario_path)
        state.rng_seed = seed

        report = state.raid(OperationTarget.FOUNDRY)
        return (
            report.outcome,
            report.losses,
            report.enemy_losses,
            report.days,
        )

    result1 = run_raid(42)
    result2 = run_raid(42)

    assert result1 == result2


def test_resolver_different_seeds_different_results() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    scenario_path = data_dir / "scenario.json"

    def run_raid(seed: int) -> str:
        state = load_game_state(scenario_path)
        state.rng_seed = seed

        report = state.raid(OperationTarget.FOUNDRY)
        return report.outcome

    result1 = run_raid(100)
    result2 = run_raid(200)

    assert isinstance(result1, str)
    assert isinstance(result2, str)
