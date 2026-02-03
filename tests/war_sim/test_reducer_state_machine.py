from __future__ import annotations

from hypothesis import settings
from hypothesis.stateful import RuleBasedStateMachine, rule, precondition, invariant, run_state_machine_as_test
from hypothesis import strategies as st

from tests.helpers.factories import make_state
from tests.helpers.invariants import assert_supplies_non_negative, assert_units_non_negative
from war_sim.domain.actions import (
    AdvanceDay,
    DispatchShipment,
    QueueBarracks,
    QueueProduction,
    StartOperation,
    SubmitPhaseDecisions,
    AcknowledgePhaseReport,
)
from war_sim.domain.ops_models import OperationIntent, OperationTarget, OperationTypeId, Phase1Decisions, Phase2Decisions, Phase3Decisions
from war_sim.domain.types import LocationId, Supplies, UnitStock
from war_sim.sim.reducer import apply_action


class ReducerStateMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.state = make_state(seed=5)

    @rule(quantity=st.integers(min_value=1, max_value=10))
    def queue_production(self, quantity: int) -> None:
        result = apply_action(
            self.state,
            QueueProduction(job_type="ammo", quantity=quantity, stop_at=LocationId.NEW_SYSTEM_CORE),
        )
        assert result.ok is True

    @rule(quantity=st.integers(min_value=1, max_value=10))
    def queue_barracks(self, quantity: int) -> None:
        result = apply_action(
            self.state,
            QueueBarracks(job_type="infantry", quantity=quantity, stop_at=LocationId.NEW_SYSTEM_CORE),
        )
        assert result.ok is True

    @precondition(lambda self: self.state.action_points > 0)
    @rule()
    def dispatch_small_shipment(self) -> None:
        routes = list(self.state.logistics.routes)
        route = routes[0]
        origin = route.origin
        destination = route.destination
        stock = self.state.logistics.depot_stocks[origin]
        if stock.ammo <= 0:
            return
        supplies = Supplies(ammo=min(10, stock.ammo), fuel=0, med_spares=0)
        result = apply_action(
            self.state,
            DispatchShipment(
                origin=origin,
                destination=destination,
                supplies=supplies,
                units=UnitStock(0, 0, 0),
            ),
        )
        assert result.ok in (True, False)

    @rule()
    def advance_day(self) -> None:
        result = apply_action(self.state, AdvanceDay())
        assert result.ok in (True, False)

    @precondition(lambda self: self.state.operation is None and self.state.action_points > 0)
    @rule()
    def start_operation(self) -> None:
        intent = OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN)
        result = apply_action(self.state, StartOperation(intent=intent))
        assert result.ok in (True, False)

    @precondition(lambda self: self.state.operation is not None and self.state.operation.awaiting_player_decision)
    @rule()
    def submit_decisions(self) -> None:
        op = self.state.operation
        if op is None:
            return
        phase = op.current_phase.value
        if phase == "contact_shaping":
            decisions = Phase1Decisions(approach_axis="direct", fire_support_prep="conserve")
        elif phase == "engagement":
            decisions = Phase2Decisions(engagement_posture="methodical", risk_tolerance="med")
        else:
            decisions = Phase3Decisions(exploit_vs_secure="secure", end_state="capture")
        result = apply_action(self.state, SubmitPhaseDecisions(decisions=decisions))
        assert result.ok in (True, False)

    @precondition(
        lambda self: self.state.operation is not None and self.state.operation.pending_phase_record is not None
    )
    @rule()
    def acknowledge_phase(self) -> None:
        result = apply_action(self.state, AcknowledgePhaseReport())
        assert result.ok in (True, False)

    @invariant()
    def invariants_hold(self) -> None:
        assert self.state.day >= 1
        assert self.state.action_points >= 0
        for stock in self.state.logistics.depot_stocks.values():
            assert_supplies_non_negative(stock)
        for stock in self.state.logistics.depot_units.values():
            assert_units_non_negative(stock)
        if self.state.operation and self.state.operation.pending_phase_record is not None:
            assert self.state.operation.pending_phase_record.phase is not None


def test_reducer_state_machine() -> None:
    run_state_machine_as_test(
        ReducerStateMachine,
        settings=settings(max_examples=10, stateful_step_count=25),
    )
