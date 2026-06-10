"""Tests for the unified operation battle resolver and state effects."""

from clone_wars.engine.ops import (
    OperationIntent,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from clone_wars.engine.state import GameState
from clone_wars.engine.types import ObjectiveStatus


def run_campaign(state: GameState, target: OperationTarget):
    state.start_operation_phased(OperationIntent(target=target, op_type=OperationTypeId.CAMPAIGN))
    while state.operation is not None:
        if state.operation.pending_phase_record is not None:
            state.acknowledge_phase_result()
            continue
        if state.operation.awaiting_player_decision:
            phase = state.operation.current_phase
            if phase.value == "contact_shaping":
                state.submit_phase_decisions(
                    Phase1Decisions(approach_axis="direct", fire_support_prep="preparatory")
                )
            elif phase.value == "engagement":
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


def test_raid_consumes_supplies() -> None:
    state = GameState.new(seed=1)
    state.contested_planet.enemy.infantry = 1
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    initial = state.front_supplies
    report = run_campaign(state, OperationTarget.FOUNDRY)

    assert state.front_supplies.ammo <= initial.ammo
    assert state.front_supplies.fuel <= initial.fuel
    assert state.front_supplies.med_spares <= initial.med_spares
    assert report.remaining_supplies == state.front_supplies


def test_raid_applies_casualties_to_both_sides() -> None:
    state = GameState.new(seed=42)
    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.contested_planet.enemy.infantry = 1000
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    report = run_campaign(state, OperationTarget.FOUNDRY)

    assert report.losses > 0
    assert state.task_force.composition.infantry < 1000
    assert report.enemy_losses > 0 or state.contested_planet.enemy.cohesion < 1.0


def test_raid_progresses_objective_on_victory() -> None:
    state = GameState.new(seed=7)
    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.contested_planet.enemy.infantry = 10
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    report = run_campaign(state, OperationTarget.FOUNDRY)
    assert report.outcome in {"CAPTURED", "DESTROYED", "FAILED"}
    if report.outcome == "FAILED":
        assert state.contested_planet.objectives.foundry == ObjectiveStatus.ENEMY
    else:
        assert state.contested_planet.objectives.foundry == ObjectiveStatus.SECURED
