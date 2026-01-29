from __future__ import annotations

from typing import Iterable

from clone_wars.engine.barracks import BarracksJob
from clone_wars.engine.production import ProductionJob
from clone_wars.engine.logistics import CargoShip, Shipment, TransportOrder
from clone_wars.engine.ops import (
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from clone_wars.engine.state import AfterActionReport, GameState, RaidReport
from clone_wars.engine.types import LocationId, Supplies, UnitStock
from clone_wars.web.api import schemas


NODE_ORDER = [
    LocationId.NEW_SYSTEM_CORE,
    LocationId.DEEP_SPACE,
    LocationId.CONTESTED_SPACEPORT,
    LocationId.CONTESTED_MID_DEPOT,
    LocationId.CONTESTED_FRONT,
]

NODE_META = {
    LocationId.NEW_SYSTEM_CORE: ("Core Hub", "core", (8, 50)),
    LocationId.DEEP_SPACE: ("Deep Space", "deep", (30, 35)),
    LocationId.CONTESTED_SPACEPORT: ("Spaceport", "tactical", (52, 46)),
    LocationId.CONTESTED_MID_DEPOT: ("Mid Depot", "tactical", (70, 60)),
    LocationId.CONTESTED_FRONT: ("Contested Front", "tactical", (90, 48)),
}


def build_state_response(state: GameState) -> schemas.GameStateResponse:
    return schemas.GameStateResponse(
        day=state.day,
        action_points=state.action_points,
        faction_turn=state.faction_turn.value,
        system_nodes=_system_nodes(),
        contested_planet=_contested_planet(state),
        task_force=_task_force(state),
        production=_production_state(state),
        barracks=_barracks_state(state),
        logistics=_logistics_state(state),
        operation=_operation_state(state),
        raid=_raid_state(state),
        last_aar=_last_aar(state),
    )


def _system_nodes() -> list[schemas.SystemNode]:
    nodes: list[schemas.SystemNode] = []
    for node in NODE_ORDER:
        label, kind, pos = NODE_META[node]
        nodes.append(
            schemas.SystemNode(
                id=node.value,
                label=label,
                kind=kind,
                description=f"{label} staging point",
                position=schemas.Position(x=float(pos[0]), y=float(pos[1])),
            )
        )
    return nodes


def _estimate_range(actual: int, confidence: float) -> schemas.IntelRange:
    confidence = max(0.0, min(1.0, confidence))
    variance = int(round(actual * (1.0 - confidence) * 0.5))
    low = max(0, actual - variance)
    high = actual + variance
    return schemas.IntelRange(min=low, max=high, actual=actual)


def _contested_planet(state: GameState) -> schemas.ContestedPlanet:
    planet = state.contested_planet
    enemy = planet.enemy
    return schemas.ContestedPlanet(
        control=planet.control,
        objectives=[
            schemas.PlanetObjective(id="foundry", label="Droid Foundry", status=planet.objectives.foundry.value),
            schemas.PlanetObjective(id="comms", label="Communications Array", status=planet.objectives.comms.value),
            schemas.PlanetObjective(id="power", label="Power Plant", status=planet.objectives.power.value),
        ],
        enemy=schemas.EnemyIntel(
            infantry=_estimate_range(enemy.infantry, enemy.intel_confidence),
            walkers=_estimate_range(enemy.walkers, enemy.intel_confidence),
            support=_estimate_range(enemy.support, enemy.intel_confidence),
            fortification=enemy.fortification,
            reinforcement_rate=enemy.reinforcement_rate,
            cohesion=enemy.cohesion,
            intel_confidence=enemy.intel_confidence,
        ),
    )


def _task_force(state: GameState) -> schemas.TaskForce:
    tf = state.task_force
    return schemas.TaskForce(
        composition=_units(tf.composition),
        readiness=tf.readiness,
        cohesion=tf.cohesion,
        location=tf.location.value,
        supplies=_supplies(tf.supplies),
    )


def _production_state(state: GameState) -> schemas.ProductionState:
    jobs = _production_jobs(state.production.jobs, state.production.get_eta_summary())
    return schemas.ProductionState(
        factories=state.production.factories,
        max_factories=state.production.max_factories,
        slots_per_factory=state.production.slots_per_factory,
        capacity=state.production.capacity,
        costs=state.production.costs,
        jobs=jobs,
    )


def _barracks_state(state: GameState) -> schemas.BarracksState:
    jobs = _barracks_jobs(state.barracks.jobs, state.barracks.get_eta_summary())
    return schemas.BarracksState(
        barracks=state.barracks.barracks,
        max_barracks=state.barracks.max_barracks,
        slots_per_barracks=state.barracks.slots_per_barracks,
        capacity=state.barracks.capacity,
        costs=state.barracks.costs,
        jobs=jobs,
    )


def _logistics_state(state: GameState) -> schemas.LogisticsState:
    depots = []
    for node in NODE_ORDER:
        stock = state.logistics.depot_stocks[node]
        units = state.logistics.depot_units[node]
        label = node.value.replace("contested_", "").replace("new_system_", "").replace("_", " ").strip()
        depots.append(
            schemas.Depot(id=node.value, label=label, supplies=_supplies(stock), units=_units(units))
        )
    routes = [
        schemas.Route(
            origin=route.origin.value,
            destination=route.destination.value,
            travel_days=route.travel_days,
            interdiction_risk=route.interdiction_risk,
        )
        for route in state.logistics.routes
    ]
    shipments = [_shipment(shipment) for shipment in state.logistics.shipments]
    ships = [_ship(ship) for ship in state.logistics.ships.values()]
    orders = [_order(order) for order in state.logistics.active_orders]
    log = [
        schemas.TransitLogEntry(day=entry.day, message=entry.message, event_type=entry.event_type)
        for entry in state.logistics.transit_log
    ]
    return schemas.LogisticsState(
        depots=depots,
        routes=routes,
        shipments=shipments,
        ships=ships,
        active_orders=orders,
        transit_log=log,
    )


def _shipment(shipment: Shipment) -> schemas.Shipment:
    return schemas.Shipment(
        id=shipment.shipment_id,
        origin=shipment.origin.value,
        destination=shipment.destination.value,
        days_remaining=shipment.days_remaining,
        total_days=shipment.total_days,
        interdicted=shipment.interdicted,
        interdiction_loss_pct=shipment.interdiction_loss_pct,
        supplies=_supplies(shipment.supplies),
        units=_units(shipment.units),
    )


def _ship(ship: CargoShip) -> schemas.CargoShip:
    return schemas.CargoShip(
        id=ship.ship_id,
        name=ship.name,
        location=ship.location.value,
        state=ship.state.value,
        destination=ship.destination.value if ship.destination else None,
        days_remaining=ship.days_remaining,
        total_days=ship.total_days,
        supplies=_supplies(ship.supplies),
        units=_units(ship.units),
    )


def _order(order: TransportOrder) -> schemas.TransportOrder:
    return schemas.TransportOrder(
        order_id=order.order_id,
        origin=order.origin.value,
        final_destination=order.final_destination.value,
        current_location=order.current_location.value,
        status=order.status,
        supplies=_supplies(order.supplies),
        units=_units(order.units),
        in_transit_leg=(
            (order.in_transit_leg[0].value, order.in_transit_leg[1].value)
            if order.in_transit_leg
            else None
        ),
        carrier_id=order.carrier_id,
    )


def _operation_state(state: GameState) -> schemas.OperationState | None:
    op = state.operation
    if op is None:
        return None

    decisions_summary = schemas.OperationDecisionSummary(
        phase1=_decision_phase1(op.decisions.phase1),
        phase2=_decision_phase2(op.decisions.phase2),
        phase3=_decision_phase3(op.decisions.phase3),
    )

    return schemas.OperationState(
        target=op.target.value,
        op_type=op.op_type.value,
        current_phase=op.current_phase.value,
        estimated_total_days=op.estimated_total_days,
        phase_durations={phase.value: days for phase, days in op.phase_durations.items()},
        day_in_operation=op.day_in_operation,
        day_in_phase=op.day_in_phase,
        awaiting_decision=op.awaiting_player_decision,
        pending_phase_record=_phase_record(op.pending_phase_record),
        decisions=decisions_summary,
        phase_history=[record for record in (_phase_record(r) for r in op.phase_history) if record is not None],
        sampled_enemy_strength=op.sampled_enemy_strength,
    )


def _decision_phase1(decisions: Phase1Decisions | None) -> schemas.DecisionPhase1 | None:
    if decisions is None:
        return None
    return schemas.DecisionPhase1(
        approach_axis=decisions.approach_axis,
        fire_support_prep=decisions.fire_support_prep,
    )


def _decision_phase2(decisions: Phase2Decisions | None) -> schemas.DecisionPhase2 | None:
    if decisions is None:
        return None
    return schemas.DecisionPhase2(
        engagement_posture=decisions.engagement_posture,
        risk_tolerance=decisions.risk_tolerance,
    )


def _decision_phase3(decisions: Phase3Decisions | None) -> schemas.DecisionPhase3 | None:
    if decisions is None:
        return None
    return schemas.DecisionPhase3(
        exploit_vs_secure=decisions.exploit_vs_secure,
        end_state=decisions.end_state,
    )


def _phase_record(record) -> schemas.PhaseRecord | None:
    if record is None:
        return None
    decisions = None
    if isinstance(record.decisions, Phase1Decisions):
        decisions = {
            "approach_axis": record.decisions.approach_axis,
            "fire_support_prep": record.decisions.fire_support_prep,
        }
    elif isinstance(record.decisions, Phase2Decisions):
        decisions = {
            "engagement_posture": record.decisions.engagement_posture,
            "risk_tolerance": record.decisions.risk_tolerance,
        }
    elif isinstance(record.decisions, Phase3Decisions):
        decisions = {
            "exploit_vs_secure": record.decisions.exploit_vs_secure,
            "end_state": record.decisions.end_state,
        }
    return schemas.PhaseRecord(
        phase=record.phase.value,
        start_day=record.start_day,
        end_day=record.end_day,
        decisions=decisions,
        summary=schemas.PhaseSummary(
            progress_delta=record.summary.progress_delta,
            losses=record.summary.losses,
            supplies_spent=_supplies(record.summary.supplies_spent),
            readiness_delta=record.summary.readiness_delta,
            cohesion_delta=record.summary.cohesion_delta,
        ),
        events=[
            schemas.Event(
                name=event.name,
                value=event.value,
                delta=event.delta,
                why=event.why,
                phase=event.phase,
            )
            for event in record.events
        ],
    )


def _raid_state(state: GameState) -> schemas.RaidState | None:
    session = state.raid_session
    if session is None:
        return None
    return schemas.RaidState(
        tick=session.tick,
        max_ticks=session.max_ticks,
        your_cohesion=session.your_cohesion,
        enemy_cohesion=session.enemy_cohesion,
        your_casualties=session.your_casualties_total,
        enemy_casualties=session.enemy_casualties_total,
        outcome=session.outcome,
        reason=session.reason,
        tick_log=[
            schemas.RaidTick(
                tick=entry.tick,
                event=entry.event,
                beat=entry.beat,
            )
            for entry in session.tick_log
        ],
    )


def _last_aar(state: GameState) -> schemas.AfterActionReport | schemas.RaidReport | None:
    report = state.last_aar
    if report is None:
        return None
    if isinstance(report, RaidReport):
        return schemas.RaidReport(
            kind="raid",
            outcome=report.outcome,
            reason=report.reason,
            target=report.target.value,
            ticks=report.ticks,
            your_casualties=report.your_casualties,
            enemy_casualties=report.enemy_casualties,
            your_remaining=report.your_remaining,
            enemy_remaining=report.enemy_remaining,
            supplies_used=_supplies(report.supplies_used),
            key_moments=report.key_moments,
            top_factors=[
                schemas.RaidFactor(name=factor.name, value=factor.value, why=factor.why)
                for factor in report.top_factors
            ],
        )

    if isinstance(report, AfterActionReport):
        return schemas.AfterActionReport(
            kind="operation",
            outcome=report.outcome,
            target=report.target.value,
            operation_type=report.operation_type,
            days=report.days,
            losses=report.losses,
            remaining_supplies=_supplies(report.remaining_supplies),
            top_factors=[
                schemas.TopFactor(
                    name=factor.name,
                    value=factor.value,
                    delta=factor.delta,
                    why=factor.why,
                )
                for factor in report.top_factors
            ],
            phases=[record for record in (_phase_record(p) for p in report.phases) if record is not None],
            events=[
                schemas.Event(
                    name=event.name,
                    value=event.value,
                    delta=event.delta,
                    why=event.why,
                    phase=event.phase,
                )
                for event in report.events
            ],
        )

    return None


def _production_jobs(jobs: Iterable[ProductionJob], eta_summary: list[tuple[str, int, int, str]]):
    results = []
    for job, eta in zip(jobs, eta_summary):
        results.append(
            schemas.ProductionJob(
                type=job.job_type.value,
                quantity=job.quantity,
                remaining=job.remaining,
                stop_at=job.stop_at.value,
                eta_days=eta[2],
            )
        )
    return results


def _barracks_jobs(jobs: Iterable[BarracksJob], eta_summary: list[tuple[str, int, int, str]]):
    results = []
    for job, eta in zip(jobs, eta_summary):
        results.append(
            schemas.ProductionJob(
                type=job.job_type.value,
                quantity=job.quantity,
                remaining=job.remaining,
                stop_at=job.stop_at.value,
                eta_days=eta[2],
            )
        )
    return results


def _supplies(supplies: Supplies) -> schemas.Supplies:
    return schemas.Supplies(ammo=supplies.ammo, fuel=supplies.fuel, med_spares=supplies.med_spares)


def _units(units: UnitStock) -> schemas.UnitStock:
    return schemas.UnitStock(infantry=units.infantry, walkers=units.walkers, support=units.support)
