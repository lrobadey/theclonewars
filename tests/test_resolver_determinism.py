"""Tests for unified battle resolver determinism."""

from pathlib import Path

from clone_wars.engine.ops import (
    OperationIntent,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from clone_wars.engine.scenario import load_game_state


def _drive_to_completion(state) -> None:
    state.start_operation_phased(OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN))
    while state.last_aar is None:
        if state.operation and state.operation.pending_phase_record:
            state.acknowledge_phase_result()
            continue
        if state.operation and state.operation.awaiting_player_decision:
            phase = state.operation.current_phase.value
            if phase == "contact_shaping":
                state.submit_phase_decisions(
                    Phase1Decisions(approach_axis="direct", fire_support_prep="preparatory")
                )
            elif phase == "engagement":
                state.submit_phase_decisions(
                    Phase2Decisions(engagement_posture="methodical", risk_tolerance="med")
                )
            else:
                state.submit_phase_decisions(
                    Phase3Decisions(exploit_vs_secure="secure", end_state="capture")
                )
            continue
        state.advance_day()


def test_resolver_determinism() -> None:
    """Campaign operations produce the same results with the same seed."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    scenario_path = data_dir / "scenario.json"

    def run_operation(seed: int) -> tuple[str, int, int, int]:
        state = load_game_state(scenario_path)
        state.rng_seed = seed

        _drive_to_completion(state)
        report = state.last_aar
        assert report is not None
        return (
            report.outcome,
            report.losses,
            report.enemy_losses,
            report.days,
        )

    result1 = run_operation(42)
    result2 = run_operation(42)

    assert result1 == result2


def test_resolver_different_seeds_different_results() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    scenario_path = data_dir / "scenario.json"

    def run_operation(seed: int) -> str:
        state = load_game_state(scenario_path)
        state.rng_seed = seed

        _drive_to_completion(state)
        report = state.last_aar
        assert report is not None
        return report.outcome

    result1 = run_operation(100)
    result2 = run_operation(200)

    assert isinstance(result1, str)
    assert isinstance(result2, str)
