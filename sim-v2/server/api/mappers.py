from __future__ import annotations

from typing import Iterable

from war_sim.domain.battle_models import BattleDayTick
from war_sim.domain.ops_models import Phase1Decisions, Phase2Decisions, Phase3Decisions
from war_sim.domain.reports import AfterActionReport
from war_sim.domain.types import LocationId, Supplies, UnitStock
from war_sim.sim.state import GameState
from war_sim.systems.barracks import BarracksJob
from war_sim.systems.logistics import CargoShip, Shipment, TransportOrder
from war_sim.systems.production import ProductionJob
from war_sim.view.map_view import build_map_view
from server.api import schemas


NODE_ORDER = [
    LocationId.NEW_SYSTEM_CORE,
    LocationId.DEEP_SPACE,
    LocationId.CONTESTED_SPACEPORT,
    LocationId.CONTESTED_MID_DEPOT,
    LocationId.CONTESTED_FRONT,
]

NODE_META = {
    LocationId.NEW_SYSTEM_CORE: ("Core Hub", "core", (8, 50), "Core Hub staging point"),
    LocationId.DEEP_SPACE: ("Deep Space", "deep", (30, 35), "Deep Space staging point"),
    LocationId.CONTESTED_SPACEPORT: ("Spaceport", "tactical", (52, 46), "Spaceport staging point"),
    LocationId.CONTESTED_MID_DEPOT: ("Mid Depot", "tactical", (70, 60), "Mid Depot staging point"),
    LocationId.CONTESTED_FRONT: ("Contested Front", "tactical", (90, 48), "Contested Front staging point"),
}


def build_state_response(state: GameState) -> schemas.GameStateResponse:
    return schemas.GameStateResponse(
        day=state.day,
        action_points=state.action_points,
        faction_turn=state.faction_turn.value,
        system_nodes=_system_nodes(state),
        contested_planet=_contested_planet(state),
        task_force=_task_force(state),
        production=_production_state(state),
        barracks=_barracks_state(state),
        logistics=_logistics_state(state),
        operation=_operation_state(state),
        last_aar=_last_aar(state),
        map_view=_map_view(state),
    )


def _system_nodes(state: GameState) -> list[schemas.SystemNode]:
    nodes: list[schemas.SystemNode] = []
    scenario_nodes = {}
    if state.scenario.map:
        for node in state.scenario.map.nodes:
            scenario_nodes[node.id] = node
    for node in NODE_ORDER:
        meta = NODE_META.get(node)
        label = meta[0] if meta else node.value.replace("_", " ").title()
        kind = meta[1] if meta else "tactical"
        pos = meta[2] if meta else (0, 0)
        description = meta[3] if meta else f"{label} staging point"
        if node.value in scenario_nodes:
            sn = scenario_nodes[node.value]
            label = sn.label or label
            kind = sn.kind or kind
            pos = (sn.x, sn.y)
            description = sn.description or description
        nodes.append(
            schemas.SystemNode(
                id=node.value,
                label=label,
                kind=kind,
                description=description,
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
    objectives = state.rules.objectives
    return schemas.ContestedPlanet(
        control=planet.control,
        objectives=[
            schemas.PlanetObjective(
                id="foundry",
                label=objectives.get("foundry").name if objectives.get("foundry") else "Foundry",
                status=planet.objectives.foundry.value,
            ),
            schemas.PlanetObjective(
                id="comms",
                label=objectives.get("comms").name if objectives.get("comms") else "Comms",
                status=planet.objectives.comms.value,
            ),
            schemas.PlanetObjective(
                id="power",
                label=objectives.get("power").name if objectives.get("power") else "Power",
                status=planet.objectives.power.value,
            ),
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
        depots.append(schemas.Depot(id=node.value, label=label, supplies=_supplies(stock), units=_units(units)))
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


def _map_view(state: GameState) -> schemas.MapView | None:
    view = build_map_view(state)
    if not view:
        return None
    return schemas.MapView(
        nodes=[
            schemas.MapNode(
                id=node["id"],
                label=node["label"],
                x=node["x"],
                y=node["y"],
                type=node["type"],
                size=node["size"],
                is_labeled=node["isLabeled"],
                subtitle1=node["subtitle1"],
                subtitle2=node.get("subtitle2"),
                severity=node["severity"],
            )
            for node in view.get("nodes", [])
        ],
        connections=[
            schemas.MapConnection(
                id=conn["id"],
                from_node=conn["from"],
                to_node=conn["to"],
                status=conn["status"],
                risk=conn["risk"],
                aggregated_travel_days=conn["aggregatedTravelDays"],
                underlying_legs=[
                    schemas.MapLeg(
                        origin=leg["origin"],
                        destination=leg["destination"],
                        travel_days=leg["travelDays"],
                        interdiction_risk=leg["interdictionRisk"],
                    )
                    for leg in conn.get("underlyingLegs", [])
                ]
                if conn.get("underlyingLegs")
                else None,
            )
            for conn in view.get("connections", [])
        ],
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
        in_transit_leg=((order.in_transit_leg[0].value, order.in_transit_leg[1].value) if order.in_transit_leg else None),
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
        latest_battle_day=_battle_day(op.battle_log[-1]) if op.battle_log else None,
        current_phase_days=[_battle_day(day) for day in op.battle_phase_acc.days],
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
            enemy_losses=record.summary.enemy_losses,
            supplies_spent=_supplies(record.summary.supplies_spent),
            readiness_delta=record.summary.readiness_delta,
            cohesion_delta=record.summary.cohesion_delta,
            enemy_cohesion_delta=record.summary.enemy_cohesion_delta,
        ),
        days=[_battle_day(day) for day in record.days],
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


def _last_aar(state: GameState) -> schemas.AfterActionReport | None:
    report = state.last_aar
    if report is None:
        return None
    return schemas.AfterActionReport(
        kind="operation",
        outcome=report.outcome,
        target=report.target.value,
        operation_type=report.operation_type,
        days=report.days,
        losses=report.losses,
        enemy_losses=report.enemy_losses,
        remaining_supplies=_supplies(report.remaining_supplies),
        top_factors=[
            schemas.TopFactor(name=factor.name, value=factor.value, delta=factor.delta, why=factor.why)
            for factor in report.top_factors
        ],
        phases=[record for record in (_phase_record(p) for p in report.phases) if record is not None],
        events=[
            schemas.Event(name=event.name, value=event.value, delta=event.delta, why=event.why, phase=event.phase)
            for event in report.events
        ],
    )


def _battle_day(day: BattleDayTick) -> schemas.BattleDayTick:
    return schemas.BattleDayTick(
        day_index=day.day_index,
        global_day=day.global_day,
        phase=day.phase,
        your_power=day.your_power,
        enemy_power=day.enemy_power,
        your_advantage=day.your_advantage,
        initiative=day.initiative,
        progress_delta=day.progress_delta,
        your_losses=day.your_losses,
        enemy_losses=day.enemy_losses,
        your_remaining=day.your_remaining,
        enemy_remaining=day.enemy_remaining,
        your_cohesion=day.your_cohesion,
        enemy_cohesion=day.enemy_cohesion,
        supplies=schemas.BattleSupplySnapshot(
            ammo_before=day.supplies.ammo_before,
            fuel_before=day.supplies.fuel_before,
            med_before=day.supplies.med_before,
            ammo_spent=day.supplies.ammo_spent,
            fuel_spent=day.supplies.fuel_spent,
            med_spent=day.supplies.med_spent,
            ammo_ratio=day.supplies.ammo_ratio,
            fuel_ratio=day.supplies.fuel_ratio,
            med_ratio=day.supplies.med_ratio,
            shortage_flags=day.supplies.shortage_flags,
        ),
        tags=day.tags,
    )


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
