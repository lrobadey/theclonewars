"""Tests for web viewmodel payloads."""

from clone_wars.engine.logging import Event, TopFactor, FactorScope
from clone_wars.engine.ops import (
    OperationPhase,
    OperationPhaseRecord,
    OperationTarget,
    Phase1Decisions,
    PhaseSummary,
)
from clone_wars.engine.state import AfterActionReport, GameState
from clone_wars.engine.types import Supplies
from clone_wars.web.console_controller import ConsoleController
from clone_wars.web.render.viewmodels import console_vm


def test_console_vm_operation_aar_payload() -> None:
    state = GameState.new()

    summary = PhaseSummary(
        progress_delta=0.2,
        losses=5,
        supplies_spent=Supplies(ammo=10, fuel=5, med_spares=2),
        readiness_delta=0.05,
    )
    record = OperationPhaseRecord(
        phase=OperationPhase.CONTACT_SHAPING,
        start_day=1,
        end_day=2,
        decisions=Phase1Decisions(approach_axis="direct", fire_support_prep="preparatory"),
        summary=summary,
        events=[
            Event(
                name="base_progress",
                phase="contact_shaping",
                value=0.2,
                delta="progress",
                why="Base",
                scope=FactorScope(kind="operation", id="test"),
            )
        ],
    )
    report = AfterActionReport(
        outcome="CAPTURED",
        target=OperationTarget.FOUNDRY,
        operation_type="campaign",
        days=3,
        losses=5,
        remaining_supplies=Supplies(ammo=90, fuel=80, med_spares=30),
        top_factors=[TopFactor(name="base_progress", value=0.2, delta="progress", why="Base")],
        phases=[record],
        events=list(record.events),
    )
    state.last_aar = report

    vm = console_vm(state, ConsoleController())

    assert vm["mode"] == "aar"
    assert vm["aar"]["kind"] == "operation"
    assert vm["aar"]["target"] == "DROID FOUNDRY"
    assert vm["aar"]["operation_type"] == "CAMPAIGN"
    assert vm["aar"]["phase_rows"]
