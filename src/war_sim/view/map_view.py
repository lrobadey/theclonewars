from __future__ import annotations

from war_sim.domain.types import LocationId
from war_sim.sim.state import GameState


def _strategic_node_id(system_node_id: str) -> str | None:
    if system_node_id == LocationId.NEW_SYSTEM_CORE.value:
        return LocationId.NEW_SYSTEM_CORE.value
    if system_node_id == LocationId.DEEP_SPACE.value:
        return LocationId.DEEP_SPACE.value
    if system_node_id.startswith("contested_"):
        return LocationId.CONTESTED_FRONT.value
    return None


def _status_from_risk(risk: float) -> str:
    if risk > 0.6:
        return "blocked"
    if risk > 0.3:
        return "disrupted"
    return "active"


def build_map_view(state: GameState) -> dict:
    scale_x = 1200 / 100
    scale_y = 400 / 100
    positions: dict[str, tuple[float, float]] = {}
    if state.scenario.map:
        for node in state.scenario.map.nodes:
            positions[node.id] = (node.x, node.y)

    def get_pos(node_id: str, fallback: tuple[float, float]) -> tuple[float, float]:
        return positions.get(node_id, fallback)

    core_pos = get_pos(LocationId.NEW_SYSTEM_CORE.value, (8, 50))
    deep_pos = get_pos(LocationId.DEEP_SPACE.value, (30, 35))
    contested_pos = get_pos(LocationId.CONTESTED_FRONT.value, (90, 48))

    nodes = []

    total_jobs = len(state.production.jobs) + len(state.barracks.jobs)
    if state.production.capacity == 0:
        severity = "danger"
    elif total_jobs > 0:
        severity = "warn"
    else:
        severity = "good"
    nodes.append(
        {
            "id": LocationId.NEW_SYSTEM_CORE.value,
            "label": "CORE WORLDS",
            "x": core_pos[0] * scale_x,
            "y": core_pos[1] * scale_y,
            "type": "core",
            "size": "large",
            "isLabeled": True,
            "subtitle1": "Production online" if state.production.capacity > 0 else "Production offline",
            "subtitle2": f"Factory jobs: {len(state.production.jobs)} | Barracks jobs: {len(state.barracks.jobs)}",
            "severity": severity,
        }
    )

    deep_routes = [
        route
        for route in state.logistics.routes
        if route.origin == LocationId.DEEP_SPACE or route.destination == LocationId.DEEP_SPACE
    ]
    max_risk = max(0.0, *[route.interdiction_risk for route in deep_routes])
    if max_risk > 0.6:
        deep_severity = "danger"
    elif max_risk > 0.3:
        deep_severity = "warn"
    else:
        deep_severity = "good"
    nodes.append(
        {
            "id": LocationId.DEEP_SPACE.value,
            "label": "DEEP SPACE",
            "x": deep_pos[0] * scale_x,
            "y": deep_pos[1] * scale_y,
            "type": "deep",
            "size": "medium",
            "isLabeled": True,
            "subtitle1": f"Transit orders: {len(state.logistics.active_orders)}",
            "subtitle2": f"Shipments: {len(state.logistics.shipments)} | Ships: {len(state.logistics.ships)}",
            "severity": deep_severity,
        }
    )

    control_pct = round(state.contested_planet.control * 100)
    if state.contested_planet.control < 0.3:
        contested_severity = "danger"
    elif state.contested_planet.control < 0.6:
        contested_severity = "warn"
    else:
        contested_severity = "good"
    operation_status = "No active op"
    if state.operation:
        operation_status = f"Operation: {state.operation.current_phase.value}"

    nodes.append(
        {
            "id": LocationId.CONTESTED_FRONT.value,
            "label": "CONTESTED SYSTEM",
            "x": contested_pos[0] * scale_x,
            "y": contested_pos[1] * scale_y,
            "type": "contested",
            "size": "medium",
            "isLabeled": True,
            "subtitle1": f"Control: {control_pct}%",
            "subtitle2": operation_status,
            "severity": contested_severity,
        }
    )

    aggregated = {}
    for route in state.logistics.routes:
        origin_ui = _strategic_node_id(route.origin.value)
        dest_ui = _strategic_node_id(route.destination.value)
        if not origin_ui or not dest_ui:
            continue
        if origin_ui == dest_ui:
            continue
        key = f"{origin_ui}-{dest_ui}"
        existing = aggregated.get(key)
        max_risk = max(existing["maxRisk"], route.interdiction_risk) if existing else route.interdiction_risk
        total_travel = (existing["totalTravelDays"] if existing else 0) + route.travel_days
        legs = existing["legs"] if existing else []
        aggregated[key] = {
            "from": origin_ui,
            "to": dest_ui,
            "maxRisk": max_risk,
            "totalTravelDays": total_travel,
            "legs": [
                *legs,
                {
                    "origin": route.origin.value,
                    "destination": route.destination.value,
                    "travelDays": route.travel_days,
                    "interdictionRisk": route.interdiction_risk,
                },
            ],
        }

    connections = []
    for key, value in aggregated.items():
        connections.append(
            {
                "id": key,
                "from": value["from"],
                "to": value["to"],
                "status": _status_from_risk(value["maxRisk"]),
                "risk": value["maxRisk"],
                "aggregatedTravelDays": value["totalTravelDays"],
                "underlyingLegs": value["legs"],
            }
        )

    return {"nodes": nodes, "connections": connections}
