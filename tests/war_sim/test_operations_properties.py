from __future__ import annotations

from tests.helpers.factories import make_state
from war_sim.domain.ops_models import OperationIntent, OperationTarget, OperationTypeId


def _pick_decisions(state):
    rules = state.rules
    phase1 = dict(
        approach_axis=next(iter(rules.approach_axes.keys())),
        fire_support_prep=next(iter(rules.fire_support_prep.keys())),
    )
    phase2 = dict(
        engagement_posture=next(iter(rules.engagement_postures.keys())),
        risk_tolerance=next(iter(rules.risk_tolerances.keys())),
    )
    phase3 = dict(
        exploit_vs_secure=next(iter(rules.exploit_vs_secure.keys())),
        end_state=next(iter(rules.end_states.keys())),
    )
    return phase1, phase2, phase3


def test_phase_duration_sums_to_estimate() -> None:
    state = make_state()
    intent = OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN)
    state.start_operation_phased(intent)

    op = state.operation
    assert op is not None
    total = sum(op.phase_durations.values())
    assert total == op.estimated_total_days


def test_foundry_operation_seeds_fixed_enemy_force() -> None:
    state = make_state()
    state.start_operation_phased(OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN))

    op = state.operation
    assert op is not None
    assert op.fixed_enemy_seeded is True
    assert op.battle_defender is not None
    assert op.battle_defender.infantry == 12000
    assert op.battle_defender.walkers == 180
    assert op.battle_defender.support == 1200
    assert op.battle_defender.cohesion == 0.92
    assert op.enemy_fortification_current == 1.35


def test_non_foundry_operation_rejected() -> None:
    state = make_state()
    intent = OperationIntent(target=OperationTarget.COMMS, op_type=OperationTypeId.CAMPAIGN)
    try:
        state.start_operation_phased(intent)
    except RuntimeError as exc:
        assert "Droid Foundry" in str(exc)
    else:
        raise AssertionError("Expected non-foundry target to be rejected")


def test_phased_operation_flow_and_aar_integrity() -> None:
    state = make_state()
    intent = OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN)
    state.start_operation_phased(intent)

    phase1, phase2, phase3 = _pick_decisions(state)

    while state.operation is not None:
        op = state.operation
        if op.awaiting_player_decision:
            if op.current_phase.value == "contact_shaping":
                from war_sim.domain.ops_models import Phase1Decisions

                state.submit_phase_decisions(Phase1Decisions(**phase1))
            elif op.current_phase.value == "engagement":
                from war_sim.domain.ops_models import Phase2Decisions

                state.submit_phase_decisions(Phase2Decisions(**phase2))
            elif op.current_phase.value == "exploit_consolidate":
                from war_sim.domain.ops_models import Phase3Decisions

                state.submit_phase_decisions(Phase3Decisions(**phase3))
        state.advance_day()
        if op.pending_phase_record is not None:
            state.acknowledge_phase_result()

    report = state.last_aar
    assert report is not None
    assert report.days >= 0
    assert report.phases
    for phase in report.phases:
        assert phase.start_day <= phase.end_day
        for event in phase.events:
            assert event.phase
            assert event.name
