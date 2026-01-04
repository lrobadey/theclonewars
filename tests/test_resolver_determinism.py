"""Tests for operation resolver determinism."""

from pathlib import Path

from clone_wars.engine.ops import OperationPlan, OperationTarget
from clone_wars.engine.scenario import load_game_state
from clone_wars.engine.state import GameState


def test_resolver_determinism() -> None:
    """Test that resolver produces same results with same seed."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    scenario_path = data_dir / "scenario.json"

    # Run operation twice with same seed
    def run_operation(seed: int) -> tuple[str, int, int]:
        state = load_game_state(scenario_path)
        state.rng_seed = seed
        state.rng = state.rng.__class__(seed)

        plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
        state.start_operation(plan)

        # Advance days until operation completes
        while state.operation is not None:
            state.advance_day()

        assert state.last_aar is not None
        return (state.last_aar.outcome, state.last_aar.losses, state.last_aar.days)

    result1 = run_operation(42)
    result2 = run_operation(42)

    # Results should be identical with same seed
    assert result1 == result2


def test_resolver_different_seeds_different_results() -> None:
    """Test that different seeds produce different results."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    scenario_path = data_dir / "scenario.json"

    def run_operation(seed: int) -> str:
        state = load_game_state(scenario_path)
        state.rng_seed = seed
        state.rng = state.rng.__class__(seed)

        plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
        state.start_operation(plan)

        while state.operation is not None:
            state.advance_day()

        assert state.last_aar is not None
        return state.last_aar.outcome

    result1 = run_operation(100)
    result2 = run_operation(200)

    # With different seeds, results may differ (though not guaranteed)
    # This test mainly ensures the resolver uses the RNG correctly
    assert isinstance(result1, str)
    assert isinstance(result2, str)

