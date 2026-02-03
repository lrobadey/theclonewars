from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Callable

from war_sim.domain.actions import (
    AcknowledgeAar,
    AcknowledgePhaseReport,
    Action,
    AdvanceDay,
    DispatchShipment,
    QueueBarracks,
    QueueProduction,
    RaidResolve,
    RaidTick,
    StartOperation,
    StartRaid,
    SubmitPhaseDecisions,
    UpgradeBarracks,
    UpgradeFactory,
)
from war_sim.domain.events import FactorEvent, UiEvent
from war_sim.domain.ops_models import OperationTypeId
from war_sim.domain.types import FactionId, LocationId, Supplies, UnitStock
from war_sim.sim.day_stepper import DayAdvanceError, advance_day
from war_sim.sim.rng import derive_seed
from war_sim.sim.state import GameState
from war_sim.systems import raid
from war_sim.systems.barracks import BarracksJobType
from war_sim.systems.operations import FactorLog, start_operation, start_operation_phased, submit_phase_decisions
from war_sim.systems.production import ProductionJobType


@dataclass()
class ActionResult:
    ok: bool
    message: str | None
    message_kind: str | None
    state: GameState
    ui_events: list[UiEvent]
    factor_events: list[FactorEvent]


@dataclass()
class SimContext:
    base_seed: int
    day: int
    action_seq: int

    def rng(self, stream: str, purpose: str) -> Random:
        return Random(
            derive_seed(self.base_seed, day=self.day, action_seq=self.action_seq, stream=stream, purpose=purpose)
        )


def apply_action(state: GameState, action: Action) -> ActionResult:
    ui_events: list[UiEvent] = []
    factor_events: list[FactorEvent] = []

    next_seq = state.action_seq + 1
    ctx = SimContext(base_seed=state.rng_seed, day=state.day, action_seq=next_seq)

    def ok(message: str | None, kind: str = "info") -> ActionResult:
        state.action_seq = next_seq
        return ActionResult(
            ok=True,
            message=message,
            message_kind=kind,
            state=state,
            ui_events=list(ui_events),
            factor_events=list(factor_events),
        )

    def fail(message: str) -> ActionResult:
        return ActionResult(
            ok=False,
            message=message,
            message_kind="error",
            state=state,
            ui_events=list(ui_events),
            factor_events=list(factor_events),
        )

    if isinstance(action, AdvanceDay):
        try:
            scope_id = state.operation.op_id if state.operation else "none"
            factor_log = FactorLog(scope=FactorScope(kind="operation", id=scope_id))
            advance_day(state, ctx.rng, factor_log)
            factor_events.extend(factor_log.events)
            state.action_points = 3
            return ok("Day advanced", "info")
        except DayAdvanceError as exc:
            return fail(str(exc))
        except RuntimeError as exc:
            return fail(str(exc))

    if isinstance(action, QueueProduction):
        try:
            job_type = ProductionJobType(action.job_type)
            state.production.queue_job(job_type, action.quantity, action.stop_at)
            return ok("Factory job queued", "accent")
        except ValueError as exc:
            return fail(str(exc))

    if isinstance(action, QueueBarracks):
        try:
            job_type = BarracksJobType(action.job_type)
            state.barracks.queue_job(job_type, action.quantity, action.stop_at)
            return ok("Barracks job queued", "accent")
        except ValueError as exc:
            return fail(str(exc))

    if isinstance(action, DispatchShipment):
        if state.action_points < 1:
            return fail("No action points remaining (Need 1 AP).")
        try:
            from war_sim.systems.logistics import LogisticsService

            LogisticsService().create_shipment(
                state.logistics,
                action.origin,
                action.destination,
                action.supplies,
                action.units,
                ctx.rng("logistics", "dispatch"),
                current_day=state.day,
            )
            state.action_points = max(0, state.action_points - 1)
            return ok("Shipment dispatched", "accent")
        except ValueError as exc:
            return fail(str(exc))

    if isinstance(action, UpgradeFactory):
        if state.action_points < 1:
            return fail("No action points remaining (Need 1 AP).")
        try:
            state.production.add_factory(action.count)
            state.action_points = max(0, state.action_points - 1)
            return ok("Factory upgraded", "accent")
        except ValueError as exc:
            return fail(str(exc))

    if isinstance(action, UpgradeBarracks):
        if state.action_points < 1:
            return fail("No action points remaining (Need 1 AP).")
        try:
            state.barracks.add_barracks(action.count)
            state.action_points = max(0, state.action_points - 1)
            return ok("Barracks upgraded", "accent")
        except ValueError as exc:
            return fail(str(exc))

    if isinstance(action, StartOperation):
        if state.action_points < 1:
            return fail("No action points remaining (Need 1 AP).")
        try:
            if action.intent.op_type == OperationTypeId.RAID:
                raid.start_raid(state, action.intent.target, ctx.rng("raid", "start"))
                state.action_points = max(0, state.action_points - 1)
                return ok("Raid launched", "accent")
            start_operation_phased(state, action.intent, ctx.rng("ops", "start"))
            state.action_points = max(0, state.action_points - 1)
            return ok("Operation launched", "accent")
        except (ValueError, RuntimeError) as exc:
            return fail(str(exc))

    if isinstance(action, StartRaid):
        if state.action_points < 1:
            return fail("No action points remaining (Need 1 AP).")
        try:
            raid.start_raid(state, action.target, ctx.rng("raid", "start"))
            state.action_points = max(0, state.action_points - 1)
            return ok("Raid launched", "accent")
        except (ValueError, RuntimeError) as exc:
            return fail(str(exc))

    if isinstance(action, SubmitPhaseDecisions):
        try:
            submit_phase_decisions(state, action.decisions)
            return ok("Phase orders submitted", "accent")
        except (ValueError, RuntimeError, TypeError) as exc:
            return fail(str(exc))

    if isinstance(action, AcknowledgePhaseReport):
        try:
            if state.operation is None or state.operation.pending_phase_record is None:
                return fail("No phase report")
            from war_sim.systems.operations import acknowledge_phase_result

            acknowledge_phase_result(state)
            return ok("Phase acknowledged", "info")
        except RuntimeError as exc:
            return fail(str(exc))

    if isinstance(action, RaidTick):
        try:
            raid.advance_raid_tick(state)
            return ok("Raid tick advanced", "info")
        except RuntimeError as exc:
            return fail(str(exc))

    if isinstance(action, RaidResolve):
        try:
            raid.resolve_active_raid(state)
            if state.last_aar and hasattr(state.last_aar, "events"):
                factor_events.extend(getattr(state.last_aar, "events"))
            return ok("Raid resolved", "accent")
        except RuntimeError as exc:
            return fail(str(exc))

    if isinstance(action, AcknowledgeAar):
        state.last_aar = None
        return ok("AAR acknowledged", "info")

    return fail("Unknown action")


from war_sim.domain.events import FactorScope  # noqa: E402
