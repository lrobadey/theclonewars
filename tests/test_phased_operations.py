"""Tests for phased operation flow and outcomes."""

from clone_wars.engine.ops import (
    OperationIntent,
    OperationPhase,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from clone_wars.engine.state import GameState


def _start_phased_op(state: GameState) -> None:
    intent = OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN)
    state.start_operation_phased(intent)


def _submit_phase1(state: GameState) -> None:
    state.submit_phase_decisions(
        Phase1Decisions(approach_axis="direct", fire_support_prep="preparatory")
    )


def _submit_phase2(state: GameState) -> None:
    state.submit_phase_decisions(
        Phase2Decisions(engagement_posture="methodical", risk_tolerance="med")
    )


def _submit_phase3(state: GameState) -> None:
    state.submit_phase_decisions(
        Phase3Decisions(exploit_vs_secure="secure", end_state="capture")
    )


def test_phased_operation_requires_ack_per_phase() -> None:
    state = GameState.new(seed=3)
    _start_phased_op(state)

    op = state.operation
    assert op is not None
    assert op.awaiting_player_decision is True
    assert op.current_phase == OperationPhase.CONTACT_SHAPING

    _submit_phase1(state)
    assert op.awaiting_player_decision is False
    state.advance_day()
    assert op.pending_phase_record is not None
    assert op.pending_phase_record.phase == OperationPhase.CONTACT_SHAPING
    assert op.awaiting_player_decision is True

    state.acknowledge_phase_result()
    assert op.current_phase == OperationPhase.ENGAGEMENT
    assert op.awaiting_player_decision is True

    _submit_phase2(state)
    state.advance_day()
    assert op.pending_phase_record is not None
    assert op.pending_phase_record.phase == OperationPhase.ENGAGEMENT

    state.acknowledge_phase_result()
    assert op.current_phase == OperationPhase.EXPLOIT_CONSOLIDATE

    _submit_phase3(state)
    state.advance_day()
    if op.pending_phase_record is not None:
        assert op.pending_phase_record.phase == OperationPhase.EXPLOIT_CONSOLIDATE
        state.acknowledge_phase_result()
    while state.operation is not None:
        state.advance_day()
        if state.operation and state.operation.pending_phase_record is not None:
            state.acknowledge_phase_result()
    assert state.last_aar is not None


def test_legacy_operation_auto_advances() -> None:
    state = GameState.new(seed=4)
    from clone_wars.engine.ops import OperationPlan

    state.start_operation(OperationPlan.quickstart(OperationTarget.FOUNDRY))
    assert state.operation is not None
    assert state.operation.auto_advance is True

    # Advance enough days to resolve all phases.
    for _ in range(6):
        if state.operation is None:
            break
        state.advance_day()

    assert state.operation is None
    assert state.last_aar is not None


def test_intel_confidence_increases_after_operation() -> None:
    state = GameState.new(seed=5)
    enemy = state.contested_planet.enemy
    start_conf = enemy.intel_confidence

    _start_phased_op(state)
    _submit_phase1(state)
    state.advance_day()
    state.acknowledge_phase_result()

    _submit_phase2(state)
    state.advance_day()
    state.acknowledge_phase_result()

    _submit_phase3(state)
    state.advance_day()
    if state.operation and state.operation.pending_phase_record is not None:
        state.acknowledge_phase_result()

    while state.last_aar is None:
        state.advance_day()
        if state.operation and state.operation.pending_phase_record is not None:
            state.acknowledge_phase_result()

    assert state.last_aar is not None
    assert enemy.intel_confidence >= start_conf
