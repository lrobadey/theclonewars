"""Tests for phased campaign operation dynamics."""

from clone_wars.engine.ops import (
    OperationIntent,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from clone_wars.engine.state import GameState
from clone_wars.engine.types import Supplies


def _total_infantry_loss(initial: int, state: GameState) -> int:
    return initial - state.task_force.composition.infantry


def run_campaign(state: GameState):
    state.start_operation_phased(OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN))
    while state.operation is not None:
        if state.operation.pending_phase_record is not None:
            state.acknowledge_phase_result()
            continue
        if state.operation.awaiting_player_decision:
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
    assert state.last_aar is not None
    return state.last_aar


def test_walker_screen_reduces_infantry_casualties() -> None:
    state_with = GameState.new(seed=42)
    state_with.task_force.composition.infantry = 120
    state_with.task_force.composition.walkers = 10
    state_with.contested_planet.enemy.infantry = 220
    state_with.contested_planet.enemy.walkers = 3
    state_with.contested_planet.enemy.fortification = 1.4
    run_campaign(state_with)

    state_without = GameState.new(seed=42)
    state_without.task_force.composition.infantry = 120
    state_without.task_force.composition.walkers = 0
    state_without.contested_planet.enemy.infantry = 220
    state_without.contested_planet.enemy.walkers = 3
    state_without.contested_planet.enemy.fortification = 1.4
    run_campaign(state_without)

    inf_losses_with = _total_infantry_loss(120, state_with)
    inf_losses_without = _total_infantry_loss(120, state_without)
    assert inf_losses_with <= inf_losses_without


def test_low_ammo_increases_defeat_likelihood_or_casualties() -> None:
    state_full = GameState.new(seed=100)
    state_full.task_force.composition.infantry = 50
    state_full.set_front_supplies(Supplies(ammo=100, fuel=90, med_spares=40))
    state_full.contested_planet.enemy.infantry = 50
    state_full.contested_planet.enemy.fortification = 1.0
    report_full = run_campaign(state_full)

    state_low = GameState.new(seed=100)
    state_low.task_force.composition.infantry = 50
    state_low.set_front_supplies(Supplies(ammo=20, fuel=90, med_spares=40))
    state_low.contested_planet.enemy.infantry = 50
    state_low.contested_planet.enemy.fortification = 1.0
    report_low = run_campaign(state_low)

    assert report_low.losses >= report_full.losses or report_low.outcome == "FAILED"


def test_phase_day_log_populated() -> None:
    state = GameState.new(seed=77)
    report = run_campaign(state)

    all_days = [day for phase in report.phases for day in phase.days]
    assert len(all_days) > 0
    assert all(day.phase in {"contact_shaping", "engagement", "exploit_consolidate"} for day in all_days)


def test_day_tags_include_named_signals() -> None:
    state = GameState.new(seed=42)
    state.task_force.composition.walkers = 5
    state.set_front_supplies(Supplies(ammo=20, fuel=90, med_spares=40))
    state.contested_planet.enemy.fortification = 1.3
    report = run_campaign(state)

    all_tags = {tag for phase in report.phases for day in phase.days for tag in day.tags}
    expected_tags = {"INITIATIVE", "walker_screen", "ammo_shortage", "ammo_pinch"}
    assert len(all_tags.intersection(expected_tags)) > 0


def test_top_factors_populated_on_operation_aar() -> None:
    state = GameState.new(seed=42)
    state.task_force.composition.walkers = 5
    report = run_campaign(state)

    assert len(report.top_factors) > 0
    for factor in report.top_factors:
        assert factor.name
        assert factor.why
        assert isinstance(factor.value, float)
