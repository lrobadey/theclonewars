from __future__ import annotations

from pathlib import Path

from war_sim.domain.actions import (
    AcknowledgePhaseReport,
    AdvanceDay,
    StartOperation,
    SubmitPhaseDecisions,
)
from war_sim.domain.ops_models import (
    OperationIntent,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from war_sim.rules.scenario import load_game_state
from war_sim.sim.reducer import apply_action


def _load_state():
    data_path = Path(__file__).resolve().parents[2] / "sim-v2" / "data" / "scenarios" / "default.json"
    return load_game_state(data_path)


def test_reducer_blocks_advance_during_active_operation():
    state = _load_state()
    result = apply_action(
        state,
        StartOperation(intent=OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.RAID)),
    )
    assert result.ok
    blocked = apply_action(state, AdvanceDay())
    assert blocked.ok is False


def test_determinism_raid_operation():
    s1 = _load_state()
    s2 = _load_state()

    intent = OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.RAID)
    assert apply_action(s1, StartOperation(intent=intent)).ok
    assert apply_action(s2, StartOperation(intent=intent)).ok

    _drive_to_completion(s1)
    _drive_to_completion(s2)

    report1 = s1.last_aar
    report2 = s2.last_aar
    assert report1 and report2
    assert report1.outcome == report2.outcome
    assert [f.name for f in report1.top_factors] == [f.name for f in report2.top_factors]


def test_determinism_operation():
    s1 = _load_state()
    s2 = _load_state()

    intent = OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN)
    assert apply_action(s1, StartOperation(intent=intent)).ok
    assert apply_action(s2, StartOperation(intent=intent)).ok

    _drive_to_completion(s1)
    _drive_to_completion(s2)

    assert s1.last_aar and s2.last_aar
    assert s1.last_aar.outcome == s2.last_aar.outcome
    assert [f.name for f in s1.last_aar.top_factors] == [f.name for f in s2.last_aar.top_factors]


def _drive_to_completion(state) -> None:
    while state.last_aar is None:
        if state.operation and state.operation.pending_phase_record:
            apply_action(state, AcknowledgePhaseReport())
            continue
        if state.operation and state.operation.awaiting_player_decision:
            phase = state.operation.current_phase.value
            if phase == "contact_shaping":
                apply_action(
                    state,
                    SubmitPhaseDecisions(
                        Phase1Decisions(approach_axis="direct", fire_support_prep="preparatory")
                    ),
                )
            elif phase == "engagement":
                apply_action(
                    state,
                    SubmitPhaseDecisions(
                        Phase2Decisions(engagement_posture="methodical", risk_tolerance="med")
                    ),
                )
            else:
                apply_action(
                    state,
                    SubmitPhaseDecisions(
                        Phase3Decisions(exploit_vs_secure="secure", end_state="capture")
                    ),
                )
            continue
        apply_action(state, AdvanceDay())
