from __future__ import annotations

from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.helpers.factories import make_state
from war_sim.domain.ops_models import (
    OperationIntent,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from war_sim.rules.ruleset import ObjectiveBattlefield


def _run_campaign(state):
    state.start_operation_phased(OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN))
    while state.operation is not None:
        if state.operation.pending_phase_record is not None:
            state.acknowledge_phase_result()
            continue
        if state.operation.awaiting_player_decision:
            phase = state.operation.current_phase.value
            if phase == "contact_shaping":
                state.submit_phase_decisions(Phase1Decisions(approach_axis="direct", fire_support_prep="preparatory"))
            elif phase == "engagement":
                state.submit_phase_decisions(
                    Phase2Decisions(engagement_posture="methodical", risk_tolerance="med")
                )
            elif phase == "exploit_consolidate":
                state.submit_phase_decisions(Phase3Decisions(exploit_vs_secure="secure", end_state="capture"))
            continue
        state.advance_day()
    assert state.last_aar is not None
    return state.last_aar


@given(
    seed=st.integers(min_value=1, max_value=1000),
    your_inf=st.integers(min_value=50, max_value=300),
    enemy_inf=st.integers(min_value=50, max_value=300),
)
@settings(max_examples=25)
def test_campaign_bounds_and_conservation(seed: int, your_inf: int, enemy_inf: int) -> None:
    def apply(state):
        state.task_force.composition.infantry = your_inf
        state.task_force.composition.walkers = 0
        state.task_force.composition.support = 0
        state.contested_planet.enemy.infantry = enemy_inf
        state.contested_planet.enemy.walkers = 0
        state.contested_planet.enemy.support = 0
        state.contested_planet.enemy.cohesion = 1.0
        state.contested_planet.enemy.fortification = 1.0

    state = make_state(seed=seed, apply=apply)
    initial_you = state.task_force.composition.infantry
    initial_enemy = state.contested_planet.enemy.infantry
    if state.scenario.foundry_mvp is not None:
        initial_enemy = max(initial_enemy, state.scenario.foundry_mvp.enemy_force.infantry)
    report = _run_campaign(state)

    assert report.days >= 1
    assert report.losses >= 0
    assert report.enemy_losses >= 0
    assert state.task_force.composition.infantry <= initial_you
    assert state.contested_planet.enemy.infantry <= initial_enemy
    assert 0.0 <= state.task_force.cohesion <= 1.0
    assert 0.0 <= state.contested_planet.enemy.cohesion <= 1.0


def test_campaign_determinism_same_seed() -> None:
    def apply(state):
        state.task_force.composition.infantry = 120
        state.task_force.composition.walkers = 1
        state.task_force.composition.support = 1
        state.contested_planet.enemy.infantry = 110
        state.contested_planet.enemy.walkers = 1
        state.contested_planet.enemy.support = 1

    s1 = make_state(seed=7, apply=apply)
    s2 = make_state(seed=7, apply=apply)

    r1 = _run_campaign(s1)
    r2 = _run_campaign(s2)

    assert r1.outcome == r2.outcome
    assert r1.days == r2.days
    assert r1.losses == r2.losses
    assert r1.enemy_losses == r2.enemy_losses


def test_participation_is_bounded_by_vic3_engagement_cap() -> None:
    state = make_state(seed=11)
    state.start_operation_phased(OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN))
    state.submit_phase_decisions(Phase1Decisions(approach_axis="direct", fire_support_prep="preparatory"))
    state.advance_day()

    op = state.operation
    assert op is not None
    day = op.battle_log[-1]
    cap = state.rules.battle.numeric_advantage_expansion_cap
    allowed_max = int(day.engagement_cap_manpower * (1.0 + cap))

    assert day.attacker_engaged_manpower <= allowed_max
    assert day.defender_engaged_manpower <= allowed_max


def test_low_morale_makes_side_ineligible() -> None:
    def apply(state):
        state.task_force.readiness = 1.0
        state.task_force.cohesion = 0.0

    state = make_state(seed=12, apply=apply)
    state.start_operation_phased(OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN))
    state.submit_phase_decisions(Phase1Decisions(approach_axis="direct", fire_support_prep="preparatory"))
    state.advance_day()

    op = state.operation
    assert op is not None
    day = op.battle_log[-1]
    assert day.attacker_eligible_manpower == 0
    assert day.attacker_engaged_manpower == 0


def test_foundry_terrain_reduces_progress_and_increases_losses() -> None:
    baseline = make_state(seed=21)
    terrain_off = make_state(seed=21)

    foundry = terrain_off.rules.objectives["foundry"]
    assert foundry.battlefield is not None
    flat_battlefield = ObjectiveBattlefield(
        terrain_id="flat_control",
        infrastructure=foundry.battlefield.infrastructure,
        combat_width_multiplier=foundry.battlefield.combat_width_multiplier,
        attacker_power_mult=1.0,
        defender_power_mult=1.0,
        attacker_progress_mult=1.0,
        attacker_loss_mult=1.0,
        walker_power_mult_attacker=1.0,
        walker_power_mult_defender=1.0,
    )
    terrain_off_objectives = dict(terrain_off.rules.objectives)
    terrain_off_objectives["foundry"] = replace(foundry, battlefield=flat_battlefield)
    terrain_off.rules = replace(terrain_off.rules, objectives=terrain_off_objectives)

    for state in (baseline, terrain_off):
        state.start_operation_phased(OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN))
        state.submit_phase_decisions(Phase1Decisions(approach_axis="direct", fire_support_prep="preparatory"))
        state.advance_day()

    b_day = baseline.operation.battle_log[-1]  # type: ignore[union-attr]
    f_day = terrain_off.operation.battle_log[-1]  # type: ignore[union-attr]

    assert b_day.progress_delta <= f_day.progress_delta
    assert sum(b_day.your_losses.values()) >= sum(f_day.your_losses.values())
