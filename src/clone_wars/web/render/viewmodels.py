from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from clone_wars.engine.types import LocationId
from clone_wars.engine.logistics import ShipState
from clone_wars.engine.ops import (
    OperationPhase,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.state import AfterActionReport, GameState, RaidReport
from clone_wars.web.console_controller import ConsoleController
from clone_wars.web.render.format import (
    bar,
    fmt_int,
    fmt_troops,
    pct,
    risk_label,
    status_class,
    status_label,
    sum_supplies,
    sum_units,
)


RAID_AUTO_INTERVAL_MS = 500


@dataclass(frozen=True)
class PanelSpec:
    template: str
    builder: Callable[[GameState, ConsoleController], dict]


def _estimate_count(actual: int, confidence: float) -> str:
    confidence = max(0.0, min(1.0, confidence))
    variance = int(round(actual * (1.0 - confidence) * 0.5))
    low = max(0, actual - variance)
    high = actual + variance
    if confidence > 0.9 or variance <= 0:
        return fmt_int(actual)
    return f"{fmt_int(low)}-{fmt_int(high)}"


def _objective_status_for_target(state: GameState, target: OperationTarget):
    obj = state.contested_planet.objectives
    if target == OperationTarget.FOUNDRY:
        return obj.foundry
    if target == OperationTarget.COMMS:
        return obj.comms
    return obj.power


def _objective_id_for_target(target: OperationTarget) -> str:
    if target == OperationTarget.FOUNDRY:
        return "foundry"
    if target == OperationTarget.COMMS:
        return "comms"
    return "power"


def _phase_title(phase: OperationPhase) -> str:
    titles = {
        OperationPhase.CONTACT_SHAPING: "PHASE 1: CONTACT & SHAPING",
        OperationPhase.ENGAGEMENT: "PHASE 2: MAIN ENGAGEMENT",
        OperationPhase.EXPLOIT_CONSOLIDATE: "PHASE 3: EXPLOIT & CONSOLIDATE",
    }
    return titles.get(phase, phase.value.upper())


def _phase_short(phase: OperationPhase) -> str:
    labels = {
        OperationPhase.CONTACT_SHAPING: "CONTACT & SHAPING",
        OperationPhase.ENGAGEMENT: "MAIN ENGAGEMENT",
        OperationPhase.EXPLOIT_CONSOLIDATE: "EXPLOIT & CONSOLIDATE",
    }
    return labels.get(phase, phase.value.replace("_", " ").upper())


def _decision_summary(decisions: Phase1Decisions | Phase2Decisions | Phase3Decisions | None) -> str:
    if decisions is None:
        return "DECISIONS: N/A"
    if isinstance(decisions, Phase1Decisions):
        return (
            f"AXIS {decisions.approach_axis.upper()} | "
            f"FIRE {decisions.fire_support_prep.upper()}"
        )
    if isinstance(decisions, Phase2Decisions):
        return (
            f"POSTURE {decisions.engagement_posture.upper()} | "
            f"RISK {decisions.risk_tolerance.upper()}"
        )
    return (
        f"FOCUS {decisions.exploit_vs_secure.upper()} | "
        f"END {decisions.end_state.upper()}"
    )


def _fmt_factor_value(value: float) -> str:
    return f"{value:+.2f}"


def _recommendations_from_factors(factors: list[dict[str, str]]) -> list[str]:
    recs: list[str] = []
    for factor in factors:
        name = factor.get("name", "")
        if "ammo_shortage" in name:
            rec = "Increase ammo shipments or reduce preparatory fire."
        elif "fuel_shortage" in name:
            rec = "Boost fuel throughput to maintain maneuver tempo."
        elif "med_spares_shortage" in name:
            rec = "Add med/spares or support units to sustain losses."
        elif "enemy_fortification" in name:
            rec = "Use siege posture or preparatory fires to weaken fortifications."
        elif "fog_of_war" in name or "intel" in name or "recon" in name:
            rec = "Invest in recon/support to reduce variance."
        elif "transport_protection" in name:
            rec = "Keep walkers/vehicles to screen infantry losses."
        elif "medic" in name:
            rec = "Maintain support units for sustainment and recovery."
        elif "risk_high" in name or "risk_low" in name:
            rec = "Align risk tolerance with supply and intel confidence."
        elif "approach_" in name or "posture_" in name:
            rec = "Adjust posture/approach to balance progress and losses."
        else:
            rec = ""
        if rec and rec not in recs:
            recs.append(rec)
        if len(recs) >= 3:
            break
    if not recs:
        recs.append("Maintain supply throughput and recon coverage.")
    return recs


def header_vm(state: GameState, controller: ConsoleController) -> dict:
    totals = sum_supplies(state.logistics.depot_stocks)
    unit_totals = sum_units(state.logistics.depot_units)
    max_factories = max(1, state.production.max_factories)
    ic_pct = round(100 * (state.production.factories / max_factories))
    return {
        "day": state.day,
        "ic_pct": ic_pct,
        "capacity_slots": state.production.capacity,
        "factories": state.production.factories,
        "max_factories": max_factories,
        "ap": state.action_points,
        "ap_max": 3,
        "supplies": {
            "ammo": fmt_int(totals.ammo),
            "fuel": fmt_int(totals.fuel),
            "med_spares": fmt_int(totals.med_spares),
        },
        "units": {
            "infantry": fmt_troops(unit_totals.infantry),
            "walkers": fmt_int(unit_totals.walkers),
            "support": fmt_int(unit_totals.support),
        },
    }


def navigator_vm(state: GameState, controller: ConsoleController) -> dict:
    view_mode = controller.view_mode
    nodes = [
        {"id": "view-core", "label": "CORE WORLDS", "mode": "core", "tone": "core"},
        {"id": "view-deep", "label": "DEEP SPACE", "mode": "deep", "tone": "deep"},
        {"id": "view-tactical", "label": "CONTESTED SYSTEM", "mode": "tactical", "tone": "tactical"},
    ]
    for node in nodes:
        node["active"] = node["mode"] == view_mode
    return {"nodes": nodes, "active_mode": view_mode}


def viewport_vm(state: GameState, controller: ConsoleController) -> dict:
    view_mode = controller.view_mode
    payload: dict[str, dict] = {"view_mode": view_mode}
    if view_mode == "core":
        payload["core"] = core_view_vm(state, controller)
    elif view_mode == "deep":
        payload["deep"] = deep_view_vm(state, controller)
    else:
        payload["tactical"] = tactical_view_vm(state, controller)
    return payload


def _hud_from_controls(
    controller: ConsoleController,
    controls: dict | None,
    cta: dict | None,
) -> dict:
    lines: list[dict[str, str]] = []
    actions: list[dict[str, str]] = []
    if controls:
        lines = list(controls.get("lines", []))
        actions = list(controls.get("actions", []))
    elif cta:
        actions = [cta]

    return {
        "message": controller.message,
        "message_kind": controller.message_kind,
        "lines": lines,
        "actions": actions,
        "auto_advance": False,
        "auto_interval_ms": RAID_AUTO_INTERVAL_MS,
        "aar": None,
    }


def _loc_short(loc: LocationId | None) -> str:
    if loc is None:
        return "-"
    return (
        loc.value.replace("contested_", "")
        .replace("new_system_", "")
        .replace("_", " ")
        .strip()
        .upper()
    )


def core_view_vm(state: GameState, controller: ConsoleController) -> dict:
    prod_vm = production_vm(state, controller)
    stock = state.logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE]
    units = state.logistics.depot_units[LocationId.NEW_SYSTEM_CORE]

    return {
        "factory": {
            "capacity": prod_vm["capacity"],
            "factories": prod_vm["factories"],
            "max_factories": prod_vm["max_factories"],
            "slots_per_factory": prod_vm["slots_per_factory"],
            "can_upgrade": prod_vm["can_upgrade"],
            "jobs_count": len(prod_vm["jobs"]),
        },
        "jobs": prod_vm["jobs"],
        "stockpiles": {
            "supplies": {
                "ammo": fmt_int(stock.ammo),
                "fuel": fmt_int(stock.fuel),
                "med_spares": fmt_int(stock.med_spares),
            },
            "units": {
                "infantry": fmt_troops(units.infantry),
                "walkers": fmt_int(units.walkers),
                "support": fmt_int(units.support),
            },
        },
        "hud": _hud_from_controls(controller, prod_vm["controls"], prod_vm["cta"]),
    }


def deep_view_vm(state: GameState, controller: ConsoleController) -> dict:
    ships = []
    has_transit = False
    for ship in state.logistics.ships.values():
        in_transit = ship.state == ShipState.TRANSIT
        has_transit = has_transit or in_transit
        payload = (
            f"A{fmt_int(ship.supplies.ammo)} F{fmt_int(ship.supplies.fuel)} "
            f"M{fmt_int(ship.supplies.med_spares)}"
        )
        unit_payload = (
            f"I{fmt_int(ship.units.infantry)} "
            f"W{fmt_int(ship.units.walkers)} "
            f"S{fmt_int(ship.units.support)}"
        )
        ships.append(
            {
                "name": ship.name,
                "location": _loc_short(ship.location),
                "destination": _loc_short(ship.destination) if ship.destination else "-",
                "status": ship.state.value.upper(),
                "payload": f"{payload} | {unit_payload}",
                "eta": ship.days_remaining if in_transit else "-",
                "in_transit": in_transit,
            }
        )

    log_vm = logistics_vm(state, controller)

    return {
        "ships": ships,
        "active_ships": [ship for ship in ships if ship["in_transit"]],
        "has_transit": has_transit,
        "routes": log_vm["routes"],
        "shipments": log_vm["shipments"],
        "constraints": log_vm["constraints"],
        "legend": log_vm["legend"],
        "hud": logistics_hud_vm(state, controller),
    }


def logistics_hud_vm(state: GameState, controller: ConsoleController) -> dict:
    lines: list[dict[str, str]] = []
    actions: list[dict[str, str]] = []

    def line(text: str, kind: str | None = None) -> None:
        if kind:
            lines.append({"text": text, "kind": kind})
        else:
            lines.append({"text": text})

    def action(action_id: str, label: str, tone: str | None = None) -> None:
        entry = {"id": action_id, "label": label}
        if tone:
            entry["tone"] = tone
        actions.append(entry)

    if controller.mode == "logistics:package":
        if controller.pending_route is None:
            line("SELECT A ROUTE FIRST.", "alert")
            action("btn-logistics-back", "BACK", "muted")
        else:
            origin, destination = controller.pending_route
            line(f"SHIPMENT PACKAGE {origin.value} -> {destination.value}", "title")
            action("ship-mixed-1", "MIXED (A40 F30 M15)")
            action("ship-ammo-1", "AMMO RUN (A60)")
            action("ship-fuel-1", "FUEL RUN (F50)")
            action("ship-med-1", "MED/SPARES (M30)")
            action("ship-inf-1", "INFANTRY (80 troops)")
            action("ship-walk-1", "WALKERS (W2)")
            action("ship-sup-1", "SUPPORT (S3)")
            action("ship-units-1", "MIXED UNITS (I80 W1 S2)")
            action("btn-logistics-back", "BACK", "muted")
    elif controller.mode == "logistics":
        line("SELECT ROUTE TO DISPATCH CARGO.", "muted")
    else:
        line("SELECT A ROUTE TO DISPATCH CARGO.", "muted")

    return {
        "message": controller.message,
        "message_kind": controller.message_kind,
        "lines": lines,
        "actions": actions,
        "auto_advance": False,
        "auto_interval_ms": RAID_AUTO_INTERVAL_MS,
        "aar": None,
    }


def tactical_view_vm(state: GameState, controller: ConsoleController) -> dict:
    focus = controller.selected_node or LocationId.CONTESTED_FRONT
    if focus == LocationId.CONTESTED_SPACEPORT:
        focus_key = "spaceport"
    elif focus == LocationId.CONTESTED_MID_DEPOT:
        focus_key = "mid"
    else:
        focus_key = "front"
    chain = [
        {
            "id": "focus-spaceport",
            "label": "SPACEPORT",
            "selected": focus == LocationId.CONTESTED_SPACEPORT,
        },
        {
            "id": "focus-mid",
            "label": "MID DEPOT",
            "selected": focus == LocationId.CONTESTED_MID_DEPOT,
        },
        {
            "id": "focus-front",
            "label": "THE FRONT",
            "selected": focus == LocationId.CONTESTED_FRONT,
        },
    ]

    spaceport_stock = state.logistics.depot_stocks[LocationId.CONTESTED_SPACEPORT]
    mid_stock = state.logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT]

    space_route = next(
        (
            route
            for route in state.logistics.routes
            if route.origin == LocationId.DEEP_SPACE and route.destination == LocationId.CONTESTED_SPACEPORT
        ),
        None,
    )
    mid_route = next(
        (
            route
            for route in state.logistics.routes
            if route.origin == LocationId.CONTESTED_SPACEPORT and route.destination == LocationId.CONTESTED_MID_DEPOT
        ),
        None,
    )
    front_route = next(
        (
            route
            for route in state.logistics.routes
            if route.origin == LocationId.CONTESTED_MID_DEPOT and route.destination == LocationId.CONTESTED_FRONT
        ),
        None,
    )

    docked = [
        {
            "name": ship.name,
            "payload": (
                f"A{fmt_int(ship.supplies.ammo)} "
                f"F{fmt_int(ship.supplies.fuel)} "
                f"M{fmt_int(ship.supplies.med_spares)}"
            ),
        }
        for ship in state.logistics.ships.values()
        if ship.location == LocationId.CONTESTED_SPACEPORT and ship.state == ShipState.IDLE
    ]

    selected_target = controller.target or OperationTarget.FOUNDRY
    active_target = None
    if state.operation:
        active_target = state.operation.target
    elif state.raid_target:
        active_target = state.raid_target
    if active_target:
        selected_target = active_target

    obj_nodes = []
    node_names = {
        OperationTarget.FOUNDRY: "FOUNDRY",
        OperationTarget.COMMS: "COMMS",
        OperationTarget.POWER: "POWER",
    }
    node_codes = {OperationTarget.FOUNDRY: "D", OperationTarget.COMMS: "C", OperationTarget.POWER: "P"}

    for target in (OperationTarget.FOUNDRY, OperationTarget.COMMS, OperationTarget.POWER):
        status = _objective_status_for_target(state, target)
        obj_nodes.append(
            {
                "id": f"map-{_objective_id_for_target(target)}",
                "action": f"map-{_objective_id_for_target(target)}",
                "code": node_codes[target],
                "name": node_names[target],
                "status_class": status_class(status),
                "selected": target == selected_target,
            }
        )

    return {
        "focus": focus.value,
        "focus_key": focus_key,
        "chain": chain,
        "spaceport": {
            "supplies": {
                "ammo": fmt_int(spaceport_stock.ammo),
                "fuel": fmt_int(spaceport_stock.fuel),
                "med_spares": fmt_int(spaceport_stock.med_spares),
            },
            "risk_pct": int(space_route.interdiction_risk * 100) if space_route else 0,
            "docked": docked,
        },
        "mid": {
            "supplies": {
                "ammo": fmt_int(mid_stock.ammo),
                "fuel": fmt_int(mid_stock.fuel),
                "med_spares": fmt_int(mid_stock.med_spares),
            },
            "legs": [
                {
                    "label": "SPACEPORT -> MID",
                    "days": mid_route.travel_days if mid_route else 0,
                    "risk_pct": int(mid_route.interdiction_risk * 100) if mid_route else 0,
                },
                {
                    "label": "MID -> FRONT",
                    "days": front_route.travel_days if front_route else 0,
                    "risk_pct": int(front_route.interdiction_risk * 100) if front_route else 0,
                },
            ],
        },
        "front": {
            "task_force": task_force_vm(state, controller),
            "enemy": enemy_intel_vm(state, controller),
            "objectives": obj_nodes,
        },
        "hud": console_vm(state, controller),
    }


def situation_map_vm(state: GameState, controller: ConsoleController) -> dict:
    selected_node = controller.selected_node or LocationId.CONTESTED_SPACEPORT
    
    # 1. Build System Strip (5 Nodes)
    # [ OUR CORE ] -> [ DEEP SPACE ] -> [ PLANET ] <- [ DEEP SPACE ] <- [ ENEMY CORE ]
    
    # Static definition for now, could be dynamic from state.logistics.routes
    system_nodes = [
        {
            "id": "map-select-core",
            "name": "CORE WORLDS",
            "loc_id": LocationId.NEW_SYSTEM_CORE,
            "owner": "friendly",
        },
        {
            "id": "map-select-deep",
            "name": "DEEP SPACE",
            "loc_id": LocationId.DEEP_SPACE,
            "owner": "friendly", # Or neutral?
        },
        {
            "id": "map-select-spaceport",
            "name": "CONTESTED SYSTEM",
            "loc_id": LocationId.CONTESTED_SPACEPORT,
            "owner": "contested",
        },
        # Enemy Nodes (Not fully simulated yet, placeholders)
        {
            "id": "map-select-enemy-deep", # Placeholder action
            "name": "DEEP SPACE (E)",
            "loc_id": "enemy_deep", # Fake ID
            "owner": "enemy",
        },
        {
            "id": "map-select-enemy-core", # Placeholder action
            "name": "CORE WORLDS (E)",
            "loc_id": "enemy_core", # Fake ID
            "owner": "enemy",
        },
    ]
    
    # Add active/selected state
    for node in system_nodes:
        node["selected"] = node["loc_id"] == selected_node
        # "Active" could mean where the player's attention is needed?
        node["active"] = False 

    # 2. Build Detail View based on Selection
    detail_view = {}
    
    if selected_node == LocationId.NEW_SYSTEM_CORE:
        # Show Production / Stockpile Summary
        stock = state.logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE]
        detail_view = {
            "type": "core",
            "title": "CORE INDUSTRIAL SECTOR",
            "supplies": {
                "ammo": fmt_int(stock.ammo),
                "fuel": fmt_int(stock.fuel),
                "med": fmt_int(stock.med_spares)
            },
            "factories": state.production.factories,
            "capacity": state.production.capacity,
            "jobs_count": len(state.production.jobs)
        }
        
    elif selected_node == LocationId.DEEP_SPACE:
        # Show Cargo Ships
        ships = [s for s in state.logistics.ships.values() if s.location == LocationId.DEEP_SPACE or s.destination == LocationId.DEEP_SPACE or s.location == LocationId.NEW_SYSTEM_CORE] 
        # Actually show all owned ships for now? Or just those in this sector?
        # Let's show all friendly ships to make finding them easier.
        ship_list = []
        for ship in state.logistics.ships.values():
            ship_data = {
                "name": ship.name,
                "state": ship.state.value.upper(),
                "loc": ship.location.value.split('_')[-1].upper(),
                "dest": ship.destination.value.split('_')[-1].upper() if ship.destination else "-",
                "load": {
                    "ammo": fmt_int(ship.supplies.ammo),
                    "fuel": fmt_int(ship.supplies.fuel),
                    "inf": fmt_int(ship.units.infantry),
                    "walk": fmt_int(ship.units.walkers)
                }
            }
            ship_list.append(ship_data)
            
        detail_view = {
            "type": "deep_space",
            "title": "DEEP SPACE TRANSIT",
            "ships": ship_list
        }

    else:
        # Default: Contested Environment (Spaceport/Mid/Front)
        # Combine the old "Situation Map" view with the new 3-node logistics view
        
        # 3-Node Chain Data
        chain_nodes = []
        for loc in (LocationId.CONTESTED_SPACEPORT, LocationId.CONTESTED_MID_DEPOT, LocationId.CONTESTED_FRONT):
            stock = state.logistics.depot_stocks[loc]
            name = loc.value.replace("contested_", "").upper()
            chain_nodes.append({
                "name": name,
                "selected": selected_node == loc, # Can define sub-selection if we want
                "action": f"map-select-{name.lower() if name != 'MID_DEPOT' else 'mid'}", # map-select-spaceport, map-select-mid, etc
                "supplies": {
                    "ammo": fmt_int(stock.ammo),
                    "fuel": fmt_int(stock.fuel)
                }
            })
            
        # Objectives (Existing Logic)
        selected_target = controller.target or OperationTarget.FOUNDRY
        active_target = None
        if state.operation:
            active_target = state.operation.target
        elif state.raid_target:
            active_target = state.raid_target
        if active_target:
            selected_target = active_target

        obj_nodes = []
        node_names = {
            OperationTarget.FOUNDRY: "FOUNDRY",
            OperationTarget.COMMS: "COMMS",
            OperationTarget.POWER: "POWER",
        }
        node_codes = {OperationTarget.FOUNDRY: "D", OperationTarget.COMMS: "C", OperationTarget.POWER: "P"}
        
        for target in (OperationTarget.FOUNDRY, OperationTarget.COMMS, OperationTarget.POWER):
            status = _objective_status_for_target(state, target)
            obj_nodes.append({
                "id": f"map-{_objective_id_for_target(target)}",
                "action": f"map-{_objective_id_for_target(target)}",
                "code": node_codes[target],
                "name": node_names[target],
                "status_class": status_class(status),
                "selected": target == selected_target,
            })
            
        detail_view = {
            "type": "contested",
            "title": "CONTESTED SURFACE",
            "logistics_chain": chain_nodes,
            "objectives": obj_nodes,

            "enemy_intel": enemy_intel_vm(state, controller)
        }

    return {
        "system_nodes": system_nodes,
        "detail": detail_view
    }


def enemy_intel_vm(state: GameState, controller: ConsoleController) -> dict:
    enemy = state.contested_planet.enemy
    conf = enemy.intel_confidence
    fort_label = "HIGH" if enemy.fortification >= 1.0 else "LOW"
    reinf_label = "MODERATE" if enemy.reinforcement_rate >= 0.08 else "LOW"
    return {
        "infantry_est": _estimate_count(enemy.infantry, conf),
        "walkers_est": _estimate_count(enemy.walkers, conf),
        "support_est": _estimate_count(enemy.support, conf),
        "confidence_pct": int(conf * 100),
        "cohesion_pct": int(enemy.cohesion * 100),
        "fort_label": fort_label,
        "reinf_label": reinf_label,
    }


def task_force_vm(state: GameState, controller: ConsoleController) -> dict:
    tf = state.task_force
    readiness = pct(tf.readiness)
    cohesion = pct(tf.cohesion)
    if cohesion >= 80:
        coh_label = "HIGH"
    elif cohesion >= 50:
        coh_label = "MED"
    else:
        coh_label = "LOW"

    supplies = tf.supplies
    ammo_bar = bar(supplies.ammo, 300)
    fuel_bar = bar(supplies.fuel, 200)
    med_bar = bar(supplies.med_spares, 150)

    lines = [
        "TASK FORCE: REPUBLIC HAMMER",
        f"UNITS: INFANTRY ({fmt_troops(tf.composition.infantry)}),",
        f"       WALKERS ({fmt_int(tf.composition.walkers)}), SUPPORT ({fmt_int(tf.composition.support)})",
        "",
        f"READINESS: {readiness}%",
        f"COHESION: {coh_label}",
        "",
        "SUPPLIES CARRIED:",
        f"  A: {fmt_int(supplies.ammo):>4} {ammo_bar}",
        f"  F: {fmt_int(supplies.fuel):>4} {fuel_bar}",
        f"  M: {fmt_int(supplies.med_spares):>4} {med_bar}",
    ]

    return {"text": "\n".join(lines)}


def production_vm(state: GameState, controller: ConsoleController) -> dict:
    prod = state.production
    jobs = []
    if prod.jobs:
        for job_type, quantity, eta, stop_at in prod.get_eta_summary():
            label = f"{job_type.upper()} x{fmt_int(quantity)}"
            jobs.append({"label": label, "eta": eta, "stop_at": stop_at})

    controls = _production_controls(state, controller)
    cta = None
    if controls is None:
        cta = {"id": "btn-production", "label": "QUEUE PRODUCTION", "tone": "accent"}

    return {
        "capacity": prod.capacity,
        "factories": prod.factories,
        "max_factories": prod.max_factories,
        "slots_per_factory": prod.slots_per_factory,
        "can_upgrade": prod.can_add_factory(),
        "jobs": jobs,
        "controls": controls,
        "cta": cta,
    }


def _production_controls(state: GameState, controller: ConsoleController) -> dict | None:
    mode = controller.mode
    if not mode.startswith("production"):
        return None

    lines: list[dict[str, str]] = []
    actions: list[dict[str, str]] = []

    def line(text: str, kind: str | None = None) -> None:
        if kind:
            lines.append({"text": text, "kind": kind})
        else:
            lines.append({"text": text})

    def action(action_id: str, label: str, tone: str | None = None) -> None:
        entry = {"id": action_id, "label": label}
        if tone:
            entry["tone"] = tone
        actions.append(entry)

    if mode == "production":
        line("PRODUCTION COMMAND", "title")
        line("SELECT CATEGORY:", "muted")
        action("prod-cat-supplies", "SUPPLIES")
        action("prod-cat-army", "ARMY")
        if state.production.can_add_factory():
            action("prod-upgrade-factory", "UPGRADE FACTORY (+1 SLOT)", "accent")
        action("btn-cancel", "BACK", "muted")
    elif mode == "production:item":
        if controller.prod_category is None:
            line("SELECT A CATEGORY FIRST.", "alert")
            action("btn-cancel", "BACK", "muted")
        else:
            title = controller.prod_category.upper()
            line(f"PRODUCTION - {title}", "title")
            line("SELECT ITEM:", "muted")
            if controller.prod_category == "supplies":
                action("prod-item-ammo", "AMMO")
                action("prod-item-fuel", "FUEL")
                action("prod-item-med", "MED/SPARES")
            else:
                action("prod-item-inf", "INFANTRY")
                action("prod-item-walkers", "WALKERS")
                action("prod-item-support", "SUPPORT")
            action("prod-back-category", "BACK", "muted")
    elif mode == "production:quantity":
        if controller.prod_job_type is None:
            line("SELECT AN ITEM FIRST.", "alert")
            action("prod-back-category", "BACK", "muted")
        else:
            job_label = controller.prod_job_type.value.upper()
            quantity_line = fmt_int(controller.prod_quantity)
            line("PRODUCTION - QUANTITY", "title")
            line(f"ITEM: {job_label}", "muted")
            line(f"QUANTITY: {quantity_line}", "muted")
            action("prod-qty-minus-50", "-50")
            action("prod-qty-minus-10", "-10")
            action("prod-qty-minus-1", "-1")
            action("prod-qty-plus-1", "+1")
            action("prod-qty-plus-10", "+10")
            action("prod-qty-plus-50", "+50")
            action("prod-qty-reset", "RESET")
            action("prod-qty-next", "CHOOSE DEPOT", "accent")
            action("prod-back-item", "BACK", "muted")
    elif mode == "production:stop":
        if controller.prod_job_type is None:
            line("SELECT AN ITEM FIRST.", "alert")
            action("prod-back-category", "BACK", "muted")
        else:
            job_label = controller.prod_job_type.value.upper()
            quantity_line = fmt_int(controller.prod_quantity)
            line("PRODUCTION - DELIVER TO", "title")
            line(f"ITEM: {job_label}", "muted")
            line(f"QUANTITY: {quantity_line}", "muted")
            action("prod-stop-core", "CORE")
            action("prod-stop-mid", "MID")
            action("prod-stop-front", "FRONT")
            action("prod-back-qty", "BACK", "muted")

    return {"lines": lines, "actions": actions}


def logistics_vm(state: GameState, controller: ConsoleController) -> dict:
    lines = ["LOGISTICS NETWORK"]
    stocks = state.logistics.depot_stocks
    units = state.logistics.depot_units
    storage_risk = state.rules.globals.storage_risk_per_day
    storage_loss = state.rules.globals.storage_loss_pct_range
    
    # Depots to show in the list
    depot_ids = (
        LocationId.NEW_SYSTEM_CORE, 
        LocationId.DEEP_SPACE, 
        LocationId.CONTESTED_SPACEPORT,
        LocationId.CONTESTED_MID_DEPOT,
        LocationId.CONTESTED_FRONT
    )
    
    depots = []
    for depot in depot_ids:
        # stock = state.task_force.supplies if depot == LocationId.CONTESTED_WORLD else stocks[depot] 
        # (Task Force supply logic might need revisited, but for now just show depot stocks)
        stock = stocks.get(depot, None)
        if stock is None: continue
        
        unit = units.get(depot, None)
        
        risk = storage_risk.get(depot, 0.0)
        loss_min, loss_max = storage_loss.get(depot, (0.0, 0.0))
        
        name_clean = depot.value.replace("contested_", "").replace("new_system_", "").replace("_", " ").strip().upper()
        # Edge case for CORE which might end up as "CORE"
        # "new_system_core" -> "CORE"
        
        depots.append(
            {
                "short": name_clean,
                "name": depot.value,
                "supplies": {
                    "ammo": fmt_int(stock.ammo),
                    "fuel": fmt_int(stock.fuel),
                    "med_spares": fmt_int(stock.med_spares),
                },
                "units": {
                    "infantry": fmt_int(unit.infantry),
                    "walkers": fmt_int(unit.walkers),
                    "support": fmt_int(unit.support),
                },
                "risk_label": risk_label(risk),
                "risk_pct": int(risk * 100),
                "loss_range": f"{int(loss_min * 100)}-{int(loss_max * 100)}%",
            }
        )

    # Active Shipments (Ground Convoys)
    shipments = []
    if state.logistics.shipments:
        for shipment in state.logistics.shipments:
            status = "INTERDICTED" if shipment.interdicted else "EN ROUTE"
            status_tone = "interdicted" if shipment.interdicted else "enroute"
            path = "->".join(node.value.split("_")[-1].upper() for node in shipment.path)
            leg = f"{shipment.origin.value.split('_')[-1].upper()}->{shipment.destination.value.split('_')[-1].upper()}"
            unit_seg = ""
            if shipment.units.infantry or shipment.units.walkers or shipment.units.support:
                unit_seg = (
                    f"I{shipment.units.infantry} W{shipment.units.walkers} "
                    f"S{shipment.units.support}"
                )
            shipments.append(
                {
                    "id": shipment.shipment_id,
                    "path": path,
                    "leg": leg,
                    "supplies": (
                        f"A{fmt_int(shipment.supplies.ammo)} F{fmt_int(shipment.supplies.fuel)} "
                        f"M{fmt_int(shipment.supplies.med_spares)}"
                    ),
                    "units": unit_seg,
                    "eta": shipment.days_remaining,
                    "status": status,
                    "status_tone": status_tone,
                }
            )

    # Routes (Available Actions)
    action_map = {
        (LocationId.NEW_SYSTEM_CORE, LocationId.DEEP_SPACE): "route-core-mid",
        (LocationId.DEEP_SPACE, LocationId.CONTESTED_SPACEPORT): "route-mid-front",
    }
    route_by_pair = {(route.origin, route.destination): route for route in state.logistics.routes}
    ordered_pairs = [
        (LocationId.NEW_SYSTEM_CORE, LocationId.DEEP_SPACE),
        (LocationId.DEEP_SPACE, LocationId.CONTESTED_SPACEPORT),
    ]
    routes = []
    for pair in ordered_pairs:
        route = route_by_pair.get(pair)
        if not route:
            continue
        routes.append(
            {
                "action": action_map[pair],
                "label": f"{pair[0].value.split('_')[-1].upper()} -> {pair[1].value.split('_')[-1].upper()}",
                "days": route.travel_days,
                "risk_pct": int(route.interdiction_risk * 100),
            }
        )
        
    # Fleet Status for Constraints
    total_ships = len(state.logistics.ships)
    idle_ships = sum(1 for s in state.logistics.ships.values() if s.state == "idle")

    return {
        "text": "\n".join(lines),
        "depots": depots,
        "routes": routes,
        "shipments": shipments,
        "legend": "CORE -> DEEP -> SPACEPORT | SPACEPORT -> MID -> FRONT",
        "constraints": {
            "port_used": 0, # Legacy: removed concept for now
            "port_cap": 99, # Legacy
            "hull_avail": idle_ships,
            "hull_total": total_ships,
        },
    }


def console_vm(state: GameState, controller: ConsoleController) -> dict:
    controller.sync_with_state(state)
    lines: list[dict[str, str]] = []
    actions: list[dict[str, str]] = []

    def line(text: str, kind: str | None = None) -> None:
        if kind:
            lines.append({"text": text, "kind": kind})
        else:
            lines.append({"text": text})

    def action(action_id: str, label: str, tone: str | None = None) -> None:
        entry = {"id": action_id, "label": label}
        if tone:
            entry["tone"] = tone
        actions.append(entry)

    mode = controller.mode

    if mode == "op:report":
        op = state.operation
        record = op.pending_phase_record if op else None
        if record is None:
            line("NO PHASE REPORT AVAILABLE.", "muted")
            action("btn-phase-ack", "[ACKNOWLEDGE]", "accent")
        else:
            line(f"{_phase_title(record.phase)} REPORT", "title")
            line(f"DAYS: {record.start_day}-{record.end_day}", "muted")
            line(_decision_summary(record.decisions), "muted")
            line(
                f"PROGRESS {record.summary.progress_delta:+.2f} | "
                f"LOSSES {fmt_int(record.summary.losses)} | "
                f"READINESS {record.summary.readiness_delta:+.2f}",
                "muted",
            )
            line(
                f"SUPPLIES A {fmt_int(record.summary.supplies_spent.ammo)} "
                f"F {fmt_int(record.summary.supplies_spent.fuel)} "
                f"M {fmt_int(record.summary.supplies_spent.med_spares)}",
                "muted",
            )
            if record.events:
                line("TOP FACTORS", "title")
                top_events = sorted(record.events, key=lambda ev: abs(ev.value), reverse=True)[:3]
                for ev in top_events:
                    line(f"{ev.why} ({_fmt_factor_value(ev.value)} {ev.delta})", "muted")
            action("btn-phase-ack", "[ACKNOWLEDGE]", "accent")

    elif mode == "menu":
        if state.operation is not None:
            op = state.operation
            phase_days = op.current_phase_duration()
            line(f"ALERT: OPERATION ACTIVE - {op.target.value.upper()}", "alert")
            line(
                f"{op.op_type.value.upper()} | {_phase_short(op.current_phase)}",
                "muted",
            )
            line(
                f"PHASE DAY {op.day_in_phase}/{phase_days} | "
                f"TOTAL {op.day_in_operation}/{op.estimated_days}",
                "muted",
            )
            line(
                f"PROGRESS {op.accumulated_progress:.2f} | "
                f"LOSSES {fmt_int(op.accumulated_losses)}",
                "muted",
            )
            line("USE END TURN TO ADVANCE THE OPERATION.", "muted")
        elif controller.target is not None:
            line(f"TARGET SELECTED: {controller.target.value.upper()}", "title")
            line("READY TO ISSUE ORDERS.", "muted")
        else:
            line("TACTICAL THEATER READY.", "title")
            line("SELECT AN OBJECTIVE TO BEGIN.", "muted")

    elif mode == "sector":
        if controller.target is None:
            line("NO TARGET SELECTED.", "alert")
            action("btn-sector-back", "[Q] BACK", "muted")
        else:
            target = controller.target
            status = _objective_status_for_target(state, target)
            obj_id = _objective_id_for_target(target)
            obj_def = state.rules.objectives.get(obj_id)
            obj_type = obj_def.type.upper() if obj_def else "UNKNOWN"
            difficulty = obj_def.base_difficulty if obj_def else 1.0
            description = (obj_def.description if obj_def else "").strip() or "No details available."

            enemy = state.contested_planet.enemy
            conf = enemy.intel_confidence
            control_pct = pct(state.contested_planet.control)

            line(f"SECTOR BRIEFING: {target.value.upper()}", "title")
            line(
                f"STATUS: {status_label(status)} | TYPE: {obj_type} | DIFF x{difficulty:.2f}",
                "muted",
            )
            line(
                f"ENEMY: I {_estimate_count(enemy.infantry, conf)} | "
                f"W {_estimate_count(enemy.walkers, conf)} | "
                f"S {_estimate_count(enemy.support, conf)} "
                f"({pct(conf)}% conf) | "
                f"FORT {enemy.fortification:.2f} | REINF {enemy.reinforcement_rate:.2f} | "
                f"COH {pct(enemy.cohesion)}% | CONTROL {control_pct}%",
                "muted",
            )
            line("")
            line("ON-SITE DETAILS", "title")
            line(description, "muted")
            line("")
            line("AVAILABLE ACTION", "title")
            line("RAID COST: A50 F30 M15 | MAX 12 TICKS", "muted")
            line("OPERATION COST: 1 AP | MULTI-DAY", "muted")
            action("btn-raid", "[A] EXECUTE RAID", "accent")
            action("sector-campaign", "[B] LAUNCH CAMPAIGN", "accent")
            action("sector-siege", "[C] LAUNCH SIEGE", "accent")
            action("btn-sector-back", "[Q] BACK", "muted")

    elif mode == "raid":
        session = state.raid_session
        if session is None:
            line("NO ACTIVE RAID.", "alert")
            action("btn-cancel", "[Q] BACK", "muted")
        else:
            target = state.raid_target or controller.target
            target_label = target.value.upper() if target else "UNKNOWN"
            line(f"RAID IN PROGRESS: {target_label}", "title")
            line(f"TICK {session.tick} OF {session.max_ticks}", "muted")
            line(f"AUTO ADVANCE: {'ON' if controller.raid_auto else 'OFF'}", "muted")
            line(
                f"YOUR FORCE: I {fmt_int(session.your_infantry)} | "
                f"W {fmt_int(session.your_walkers)} | "
                f"S {fmt_int(session.your_support)} | "
                f"COH {pct(session.your_cohesion)}%",
                "muted",
            )
            line(
                f"ENEMY FORCE: I {fmt_int(session.enemy_infantry)} | "
                f"W {fmt_int(session.enemy_walkers)} | "
                f"S {fmt_int(session.enemy_support)} | "
                f"COH {pct(session.enemy_cohesion)}%",
                "muted",
            )
            line(
                f"CASUALTIES: YOU {fmt_int(session.your_casualties_total)} | "
                f"ENEMY {fmt_int(session.enemy_casualties_total)}",
                "muted",
            )
            if session.tick_log:
                line("RECENT TICKS", "title")
                for t in session.tick_log[-6:]:
                    line(
                        f"T{t.tick} | P {t.your_power:.1f}/{t.enemy_power:.1f} | "
                        f"COH {pct(t.your_cohesion)}%/{pct(t.enemy_cohesion)}% | "
                        f"CAS {fmt_int(t.your_casualties)}/{fmt_int(t.enemy_casualties)} | {t.event}",
                        "muted",
                    )
            else:
                line("READY TO ENGAGE. ADVANCE TICK TO BEGIN.", "muted")
            action("btn-raid-tick", "[A] NEXT TICK", "accent")
            action("btn-raid-resolve", "[B] RESOLVE ALL", "muted")
            action(
                "btn-raid-auto",
                "[T] AUTO ON" if not controller.raid_auto else "[T] AUTO OFF",
                "muted",
            )

    elif mode == "plan:target":
        line("PHASE 0: SELECT TARGET SECTOR", "title")
        action("target-foundry", "[A] DROID FOUNDRY (Primary Ind.)")
        action("target-comms", "[B] COMM ARRAY (Intel/C2)")
        action("target-power", "[C] POWER PLANT (Infrastructure)")
        action("btn-cancel", "[Q] CANCEL", "muted")

    elif mode == "plan:type":
        if controller.target is None:
            line("SELECT A TARGET FIRST.", "alert")
            action("btn-cancel", "[Q] CANCEL", "muted")
        else:
            line("PHASE 0: SELECT OPERATION TYPE", "title")
            line(f"TARGET: {controller.target.value}", "muted")
            action("optype-campaign", "[A] CAMPAIGN (Balanced)")
            action("optype-siege", "[B] SIEGE (Slow / Safe)")
            action("btn-cancel", "[Q] CANCEL", "muted")

    elif mode == "plan:axis":
        if state.operation is not None:
            line(f"OPERATION: {state.operation.target.value.upper()} | {state.operation.op_type.value.upper()}", "muted")
        line("PHASE 1: CONTACT & SHAPING - APPROACH AXIS", "title")
        action("axis-direct", "[A] DIRECT (Fast, High Risk)")
        action("axis-flank", "[B] FLANK (Slow, Low Risk)")
        action("axis-dispersed", "[C] DISPERSED (High Variance)")
        action("axis-stealth", "[D] STEALTH (Minimal Contact)")

    elif mode == "plan:prep":
        if state.operation is not None:
            line(f"OPERATION: {state.operation.target.value.upper()} | {state.operation.op_type.value.upper()}", "muted")
        line("PHASE 1: CONTACT & SHAPING - FIRE SUPPORT", "title")
        action("prep-conserve", "[A] CONSERVE AMMO (No Bonus)")
        action("prep-preparatory", "[B] PREPARATORY BOMBARDMENT (+Effect, -Ammo)")

    elif mode == "plan:posture":
        if state.operation is not None:
            line(f"OPERATION: {state.operation.target.value.upper()} | {state.operation.op_type.value.upper()}", "muted")
        line("PHASE 2: MAIN ENGAGEMENT - POSTURE", "title")
        action("posture-shock", "[A] SHOCK (High Impact, High Casualty)")
        action("posture-methodical", "[B] METHODICAL (Balanced)")
        action("posture-siege", "[C] SIEGE (Slow, Safe)")
        action("posture-feint", "[D] FEINT (Distraction)")

    elif mode == "plan:risk":
        if state.operation is not None:
            line(f"OPERATION: {state.operation.target.value.upper()} | {state.operation.op_type.value.upper()}", "muted")
        line("PHASE 2: MAIN ENGAGEMENT - RISK TOLERANCE", "title")
        action("risk-low", "[A] LOW (Minimize Losses)")
        action("risk-med", "[B] MEDIUM (Standard Doctrine)")
        action("risk-high", "[C] HIGH (Accept Casualties for Speed)")

    elif mode == "plan:exploit":
        if state.operation is not None:
            line(f"OPERATION: {state.operation.target.value.upper()} | {state.operation.op_type.value.upper()}", "muted")
        line("PHASE 3: EXPLOIT & CONSOLIDATE - FOCUS", "title")
        action("exploit-push", "[A] PUSH (Maximize Gains)")
        action("exploit-secure", "[B] SECURE (Defend Gains)")

    elif mode == "plan:end":
        if state.operation is not None:
            line(f"OPERATION: {state.operation.target.value.upper()} | {state.operation.op_type.value.upper()}", "muted")
        line("PHASE 3: EXPLOIT & CONSOLIDATE - END STATE", "title")
        action("end-capture", "[A] CAPTURE (Hold Sector)")
        action("end-raid", "[B] RAID (Damage & Retreat)")
        action("end-destroy", "[C] DESTROY (Scorched Earth)")
        action("btn-cancel", "[Q] CANCEL", "muted")

    elif mode == "production":
        line("PRODUCTION COMMAND", "title")
        line("SELECT CATEGORY:", "muted")
        action("prod-cat-supplies", "[A] SUPPLIES")
        action("prod-cat-army", "[B] ARMY")
        action("btn-cancel", "[Q] BACK", "muted")

    elif mode == "production:item":
        if controller.prod_category is None:
            line("SELECT A CATEGORY FIRST.", "alert")
            action("btn-cancel", "[Q] BACK", "muted")
        else:
            title = controller.prod_category.upper()
            line(f"PRODUCTION - {title}", "title")
            line("SELECT ITEM:", "muted")
            if controller.prod_category == "supplies":
                action("prod-item-ammo", "[A] AMMO")
                action("prod-item-fuel", "[B] FUEL")
                action("prod-item-med", "[C] MED/SPARES")
            else:
                action("prod-item-inf", "[A] INFANTRY (Troopers)")
                action("prod-item-walkers", "[B] WALKERS")
                action("prod-item-support", "[C] SUPPORT")
            action("prod-back-category", "[Q] BACK", "muted")

    elif mode == "production:quantity":
        if controller.prod_job_type is None:
            line("SELECT AN ITEM FIRST.", "alert")
            action("prod-back-category", "[Q] BACK", "muted")
        else:
            job_label = controller.prod_job_type.value.upper()
            quantity_line = fmt_int(controller.prod_quantity)
            line("PRODUCTION - QUANTITY", "title")
            line(f"ITEM: {job_label}", "muted")
            line(f"QUANTITY: {quantity_line}", "muted")
            action("prod-qty-minus-50", "[-50]")
            action("prod-qty-minus-10", "[-10]")
            action("prod-qty-minus-1", "[-1]")
            action("prod-qty-plus-1", "[+1]")
            action("prod-qty-plus-10", "[+10]")
            action("prod-qty-plus-50", "[+50]")
            action("prod-qty-reset", "[RESET]")
            action("prod-qty-next", "[NEXT] CHOOSE DEPOT", "accent")
            action("prod-back-item", "[Q] BACK", "muted")

    elif mode == "production:stop":
        if controller.prod_job_type is None:
            line("SELECT AN ITEM FIRST.", "alert")
            action("prod-back-category", "[Q] BACK", "muted")
        else:
            job_label = controller.prod_job_type.value.upper()
            quantity_line = fmt_int(controller.prod_quantity)
            line("PRODUCTION - DELIVER TO", "title")
            line(f"ITEM: {job_label}", "muted")
            line(f"QUANTITY: {quantity_line}", "muted")
            action("prod-stop-core", "[A] CORE")
            action("prod-stop-mid", "[B] MID")
            action("prod-stop-front", "[C] FRONT")
            action("prod-back-qty", "[Q] BACK", "muted")

    elif mode == "logistics":
        line("LOGISTICS COMMAND", "title")
        line("SELECT ROUTE TO CREATE SHIPMENT:", "muted")
        action("route-core-mid", "[A] CORE -> MID")
        action("route-mid-front", "[B] MID -> FRONT")
        action("btn-cancel", "[Q] BACK", "muted")

    elif mode == "logistics:package":
        if controller.pending_route is None:
            line("SELECT A ROUTE FIRST.", "alert")
            action("btn-logistics-back", "[Q] BACK", "muted")
        else:
            origin, destination = controller.pending_route
            line(f"SHIPMENT PACKAGE {origin.value} -> {destination.value}", "title")
            action("ship-mixed-1", "[A] MIXED (A40 F30 M15)")
            action("ship-ammo-1", "[B] AMMO RUN (A60)")
            action("ship-fuel-1", "[C] FUEL RUN (F50)")
            action("ship-med-1", "[D] MED/SPARES (M30)")
            action("ship-inf-1", "[E] INFANTRY (80 troops)")
            action("ship-walk-1", "[F] WALKERS (W2)")
            action("ship-sup-1", "[G] SUPPORT (S3)")
            action("ship-units-1", "[H] MIXED UNITS (I80 W1 S2)")
            action("btn-logistics-back", "[Q] BACK", "muted")

    elif mode == "aar":
        report = state.last_aar
        if report is None:
            line("NO AFTER ACTION REPORT AVAILABLE.", "muted")
            action("btn-ack", "[ACKNOWLEDGE]", "accent")
        elif isinstance(report, RaidReport):
            outcome_kind = "success" if report.outcome == "VICTORY" else "failure"
            actions.append({"id": "btn-ack", "label": "[ACKNOWLEDGE]", "tone": "accent"})

            tick_rows = [
                {
                    "tick": t.tick,
                    "your_power": f"{t.your_power:.1f}",
                    "enemy_power": f"{t.enemy_power:.1f}",
                    "your_coh": f"{pct(t.your_cohesion)}%",
                    "enemy_coh": f"{pct(t.enemy_cohesion)}%",
                    "your_cas": fmt_int(t.your_casualties),
                    "enemy_cas": fmt_int(t.enemy_casualties),
                    "event": t.event,
                }
                for t in report.tick_log
            ]

            return {
                "mode": mode,
                "message": controller.message,
                "message_kind": controller.message_kind,
                "lines": [],
                "actions": actions,
                "auto_advance": False,
                "auto_interval_ms": RAID_AUTO_INTERVAL_MS,
                "aar": {
                    "kind": "raid",
                    "outcome": report.outcome,
                    "outcome_kind": outcome_kind,
                    "target": report.target.value.upper(),
                    "reason": report.reason,
                    "duration_label": "TICKS",
                    "duration": report.ticks,
                    "your_casualties": fmt_int(report.your_casualties),
                    "enemy_casualties": fmt_int(report.enemy_casualties),
                    "your_remaining": {
                        "infantry": fmt_troops(report.your_remaining["infantry"]),
                        "walkers": fmt_int(report.your_remaining["walkers"]),
                        "support": fmt_int(report.your_remaining["support"]),
                    },
                    "enemy_remaining": {
                        "infantry": fmt_troops(report.enemy_remaining["infantry"]),
                        "walkers": fmt_int(report.enemy_remaining["walkers"]),
                        "support": fmt_int(report.enemy_remaining["support"]),
                    },
                    "supplies_used": {
                        "ammo": fmt_int(report.supplies_used.ammo),
                        "fuel": fmt_int(report.supplies_used.fuel),
                        "med_spares": fmt_int(report.supplies_used.med_spares),
                    },
                    "key_moments": list(report.key_moments),
                    "tick_rows": tick_rows,
                },
            }
        elif isinstance(report, AfterActionReport):
            outcome = report.outcome
            outcome_kind = (
                "success" if any(token in outcome for token in ("CAPTURED", "RAIDED", "DESTROYED")) else "failure"
            )
            factor_rows = [
                {
                    "name": factor.name,
                    "value": _fmt_factor_value(factor.value),
                    "delta": factor.delta.upper(),
                    "why": factor.why,
                }
                for factor in report.top_factors[:5]
            ]
            phase_rows = []
            for record in report.phases:
                phase_rows.append(
                    {
                        "phase": _phase_short(record.phase),
                        "days": f"{record.start_day}-{record.end_day}",
                        "decisions": _decision_summary(record.decisions),
                        "progress": _fmt_factor_value(record.summary.progress_delta),
                        "losses": fmt_int(record.summary.losses),
                        "supplies": (
                            f"A {fmt_int(record.summary.supplies_spent.ammo)} "
                            f"F {fmt_int(record.summary.supplies_spent.fuel)} "
                            f"M {fmt_int(record.summary.supplies_spent.med_spares)}"
                        ),
                        "readiness": _fmt_factor_value(record.summary.readiness_delta),
                    }
                )
            recommendations = _recommendations_from_factors(factor_rows)
            actions.append({"id": "btn-ack", "label": "[ACKNOWLEDGE]", "tone": "accent"})
            return {
                "mode": mode,
                "message": controller.message,
                "message_kind": controller.message_kind,
                "lines": [],
                "actions": actions,
                "auto_advance": False,
                "auto_interval_ms": RAID_AUTO_INTERVAL_MS,
                "aar": {
                    "kind": "operation",
                    "outcome": outcome,
                    "outcome_kind": outcome_kind,
                    "target": report.target.value.upper(),
                    "operation_type": report.operation_type.upper(),
                    "duration_label": "DAYS",
                    "duration": report.days,
                    "losses": fmt_int(report.losses),
                    "remaining_supplies": {
                        "ammo": fmt_int(report.remaining_supplies.ammo),
                        "fuel": fmt_int(report.remaining_supplies.fuel),
                        "med_spares": fmt_int(report.remaining_supplies.med_spares),
                    },
                    "top_factors": factor_rows,
                    "phase_rows": phase_rows,
                    "recommendations": recommendations,
                },
            }

    else:
        line("UNKNOWN CONSOLE MODE.", "alert")
        action("btn-cancel", "[Q] BACK", "muted")

    return {
        "mode": mode,
        "message": controller.message,
        "message_kind": controller.message_kind,
        "lines": lines,
        "actions": actions,
        "auto_advance": controller.raid_auto and state.raid_session is not None and mode == "raid",
        "auto_interval_ms": RAID_AUTO_INTERVAL_MS,
    }


PANEL_SPECS: dict[str, PanelSpec] = {
    "header": PanelSpec(template="panels/header.html", builder=header_vm),
    "navigator": PanelSpec(template="panels/navigator.html", builder=navigator_vm),
    "viewport": PanelSpec(template="panels/viewport.html", builder=viewport_vm),
}
