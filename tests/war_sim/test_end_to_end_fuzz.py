from __future__ import annotations

from random import Random

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


def _decisions(state):
    rules = state.rules
    p1 = Phase1Decisions(
        approach_axis=next(iter(rules.approach_axes.keys())),
        fire_support_prep=next(iter(rules.fire_support_prep.keys())),
    )
    p2 = Phase2Decisions(
        engagement_posture=next(iter(rules.engagement_postures.keys())),
        risk_tolerance=next(iter(rules.risk_tolerances.keys())),
    )
    p3 = Phase3Decisions(
        exploit_vs_secure=next(iter(rules.exploit_vs_secure.keys())),
        end_state=next(iter(rules.end_states.keys())),
    )
    return p1, p2, p3


def test_end_to_end_fuzz_simulation() -> None:
    seeds = [11, 29, 61]
    for seed in seeds:
        rng = Random(seed)
        state = make_state(seed=seed)
        p1, p2, p3 = _decisions(state)

        for _ in range(12):
            # If awaiting decisions, submit and acknowledge promptly.
            if state.operation and state.operation.awaiting_player_decision:
                phase = state.operation.current_phase.value
                if phase == "contact_shaping":
                    apply_action(state, SubmitPhaseDecisions(decisions=p1))
                elif phase == "engagement":
                    apply_action(state, SubmitPhaseDecisions(decisions=p2))
                else:
                    apply_action(state, SubmitPhaseDecisions(decisions=p3))

            if state.operation and state.operation.pending_phase_record is not None:
                apply_action(state, AcknowledgePhaseReport())

            choice = rng.choice(["advance", "prod", "barracks", "dispatch", "start_op"])
            if choice == "prod":
                apply_action(
                    state,
                    QueueProduction(
                        job_type="ammo",
                        quantity=rng.randint(1, 5),
                        stop_at=LocationId.NEW_SYSTEM_CORE,
                    ),
                )
            elif choice == "barracks":
                apply_action(
                    state,
                    QueueBarracks(
                        job_type="infantry",
                        quantity=rng.randint(1, 5),
                        stop_at=LocationId.NEW_SYSTEM_CORE,
                    ),
                )
            elif choice == "dispatch" and state.action_points > 0:
                route = state.logistics.routes[0]
                stock = state.logistics.depot_stocks[route.origin]
                if stock.ammo > 0:
                    supplies = Supplies(ammo=min(5, stock.ammo), fuel=0, med_spares=0)
                    apply_action(
                        state,
                        DispatchShipment(
                            origin=route.origin,
                            destination=route.destination,
                            supplies=supplies,
                            units=UnitStock(0, 0, 0),
                        ),
                    )
            elif choice == "start_op" and state.operation is None and state.action_points > 0:
                intent = OperationIntent(target=OperationTarget.FOUNDRY, op_type=OperationTypeId.CAMPAIGN)
                apply_action(state, StartOperation(intent=intent))
            else:
                apply_action(state, AdvanceDay())

            # Invariants
            assert state.day >= 1
            assert state.action_points >= 0
            for stock in state.logistics.depot_stocks.values():
                assert_supplies_non_negative(stock)
            for stock in state.logistics.depot_units.values():
                assert_units_non_negative(stock)
