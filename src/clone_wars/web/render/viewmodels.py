from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from clone_wars.engine.logistics import DepotNode, STORAGE_LOSS_PCT_RANGE, STORAGE_RISK_PER_DAY
from clone_wars.engine.ops import OperationTarget, OperationTypeId
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.state import GameState
from clone_wars.engine.types import SQUAD_SIZE
from clone_wars.web.console_controller import ConsoleController
from clone_wars.web.render.format import (
    bar,
    fmt_int,
    fmt_squads,
    pct,
    risk_label,
    status_class,
    status_label,
    sum_supplies,
    sum_units,
)


SCHEMATIC_ART = (
    "+------------------------------------+\n"
    "| . . . . . . . . . . . . . . . . . |\n"
    "| . . . . . . . . . . . . . . . . . |\n"
    "| . . . . . . . . . . . . . . . . . |\n"
    "| . . . . . . . . . . . . . . . . . |\n"
    "| . . . . . . . . . . . . . . . . . |\n"
    "| . . . . . . . . . . . . . . . . . |\n"
    "| . . . . . . . . . . . . . . . . . |\n"
    "| . . . . . . . . . . . . . . . . . |\n"
    "+------------------------------------+"
)


@dataclass(frozen=True)
class PanelSpec:
    template: str
    builder: Callable[[GameState, ConsoleController], dict]


def _objective_status_for_target(state: GameState, target: OperationTarget):
    obj = state.planet.objectives
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


def header_vm(state: GameState, controller: ConsoleController) -> dict:
    totals = sum_supplies(state.logistics.depot_stocks)
    unit_totals = sum_units(state.logistics.depot_units)
    ic_pct = min(99, max(10, state.production.capacity * 25))
    return {
        "day": state.day,
        "ic_pct": ic_pct,
        "supplies": {
            "ammo": fmt_int(totals.ammo),
            "fuel": fmt_int(totals.fuel),
            "med_spares": fmt_int(totals.med_spares),
        },
        "units": {
            "infantry": fmt_squads(unit_totals.infantry),
            "walkers": fmt_int(unit_totals.walkers),
            "support": fmt_int(unit_totals.support),
        },
    }


def situation_map_vm(state: GameState, controller: ConsoleController) -> dict:
    selected_target = controller.target or OperationTarget.FOUNDRY
    active_target = None
    if state.operation is not None:
        active_target = state.operation.target
        selected_target = active_target

    nodes = []
    node_names = {
        OperationTarget.FOUNDRY: "FOUNDRY",
        OperationTarget.COMMS: "COMMS",
        OperationTarget.POWER: "POWER",
    }
    node_codes = {
        OperationTarget.FOUNDRY: "D",
        OperationTarget.COMMS: "C",
        OperationTarget.POWER: "P",
    }
    for target in (OperationTarget.FOUNDRY, OperationTarget.COMMS, OperationTarget.POWER):
        status = _objective_status_for_target(state, target)
        obj_id = _objective_id_for_target(target)
        obj_def = state.rules.objectives.get(obj_id)
        obj_type = obj_def.type.upper() if obj_def else "UNKNOWN"
        difficulty = f"{(obj_def.base_difficulty if obj_def else 1.0):.2f}"
        nodes.append(
            {
                "id": f"map-{_objective_id_for_target(target)}",
                "action": f"map-{_objective_id_for_target(target)}",
                "code": node_codes[target],
                "name": node_names[target],
                "type": obj_type,
                "difficulty": difficulty,
                "status_label": status_label(status),
                "status_class": status_class(status),
                "selected": target == selected_target,
                "active": target == active_target,
            }
        )

    selected_status = _objective_status_for_target(state, selected_target)
    obj_id = _objective_id_for_target(selected_target)
    obj_def = state.rules.objectives.get(obj_id)
    obj_type = obj_def.type.upper() if obj_def else "UNKNOWN"
    difficulty = f"{(obj_def.base_difficulty if obj_def else 1.0):.2f}"
    description = (obj_def.description if obj_def else "").strip()
    desc_line = description.splitlines()[0].strip() if description else "No details available."
    enemy = state.planet.enemy
    strength_range = f"{enemy.strength_min:.1f} - {enemy.strength_max:.1f}"

    return {
        "art": SCHEMATIC_ART,
        "nodes": nodes,
        "enemy": {
            "strength_range": strength_range,
            "confidence_pct": pct(enemy.confidence),
            "control_pct": pct(state.planet.control),
            "fortification": f"{enemy.fortification:.2f}",
            "reinforcement": f"{enemy.reinforcement_rate:.2f}",
        },
        "hint": "Click a node for sector briefing. Plan ops in the console.",
        "selected": {
            "name": selected_target.value.upper(),
            "status_label": status_label(selected_status),
            "status_class": status_class(selected_status),
            "type": obj_type,
            "difficulty": difficulty,
            "description": desc_line,
        },
    }


def enemy_intel_vm(state: GameState, controller: ConsoleController) -> dict:
    enemy = state.planet.enemy
    fort_label = "HIGH" if enemy.fortification >= 1.0 else "LOW"
    reinf_label = "MODERATE" if enemy.reinforcement_rate >= 0.08 else "LOW"
    return {
        "strength_range": f"{enemy.strength_min:.1f} - {enemy.strength_max:.1f}",
        "confidence_pct": int(enemy.confidence * 100),
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
        f"UNITS: INFANTRY ({fmt_squads(tf.composition.infantry)}),",
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
            if job_type == "infantry":
                label = f"{job_type.upper()} x{quantity} squads ({fmt_int(quantity * SQUAD_SIZE)} troops)"
            else:
                label = f"{job_type.upper()} x{quantity}"
            jobs.append({"label": label, "eta": eta, "stop_at": stop_at})

    controls = _production_controls(state, controller)
    cta = None
    if controls is None:
        cta = {"id": "btn-production", "label": "QUEUE PRODUCTION", "tone": "accent"}

    return {
        "capacity": prod.capacity,
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
                action("prod-item-inf", "INFANTRY (SQUADS)")
                action("prod-item-walkers", "WALKERS")
                action("prod-item-support", "SUPPORT")
            action("prod-back-category", "BACK", "muted")
    elif mode == "production:quantity":
        if controller.prod_job_type is None:
            line("SELECT AN ITEM FIRST.", "alert")
            action("prod-back-category", "BACK", "muted")
        else:
            job_label = controller.prod_job_type.value.upper()
            quantity_line = f"{controller.prod_quantity}"
            if controller.prod_job_type == ProductionJobType.INFANTRY:
                quantity_line += f" squads ({fmt_int(controller.prod_quantity * SQUAD_SIZE)} troops)"
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
            quantity_line = f"{controller.prod_quantity}"
            if controller.prod_job_type == ProductionJobType.INFANTRY:
                quantity_line += f" squads ({fmt_int(controller.prod_quantity * SQUAD_SIZE)} troops)"
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
    depots = []
    for depot in DepotNode:
        stock = state.task_force.supplies if depot == DepotNode.FRONT else stocks[depot]
        unit = units[depot]
        risk = STORAGE_RISK_PER_DAY.get(depot, 0.0)
        loss_min, loss_max = STORAGE_LOSS_PCT_RANGE.get(depot, (0.0, 0.0))
        depots.append(
            {
                "short": depot.short_label,
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

    shipments = []
    if state.logistics.shipments:
        for shipment in state.logistics.shipments:
            status = "INTERDICTED" if shipment.interdicted else "EN ROUTE"
            status_tone = "interdicted" if shipment.interdicted else "enroute"
            path = "->".join(node.short_label for node in shipment.path)
            leg = f"{shipment.origin.short_label}->{shipment.destination.short_label}"
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

    action_map = {
        (DepotNode.CORE, DepotNode.MID): "route-core-mid",
        (DepotNode.MID, DepotNode.FRONT): "route-mid-front",
    }
    route_by_pair = {(route.origin, route.destination): route for route in state.logistics.routes}
    ordered_pairs = [
        (DepotNode.CORE, DepotNode.MID),
        (DepotNode.MID, DepotNode.FRONT),
    ]
    routes = []
    for pair in ordered_pairs:
        route = route_by_pair.get(pair)
        if not route:
            continue
        routes.append(
            {
                "action": action_map[pair],
                "label": f"{pair[0].short_label} -> {pair[1].short_label}",
                "days": route.travel_days,
                "risk_pct": int(route.interdiction_risk * 100),
            }
        )

    return {
        "text": "\n".join(lines),
        "depots": depots,
        "routes": routes,
        "shipments": shipments,
        "legend": "CORE -> MID -> FRONT (LEFT TO RIGHT = CLOSER TO FRONT)",
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

    if mode == "menu":
        if state.operation is not None:
            op = state.operation
            line(f"ALERT: OPERATION ACTIVE - {op.target.value.upper()}", "alert")
            line(
                f"DAY {op.day_in_operation} OF {op.estimated_days} | STATUS: IN PROGRESS",
                "muted",
            )
            line("WAITING FOR DAILY REPORTS...", "muted")
            action("btn-next", "[N] NEXT DAY", "accent")
        else:
            line("COMMAND LINK ESTABLISHED. AWAITING ORDERS.", "title")
            action("btn-plan", "[1] PLAN OFFENSIVE")
            action("btn-production", "[2] PRODUCTION")
            action("btn-logistics", "[3] LOGISTICS")
            action("btn-next", "[4] NEXT DAY", "accent")

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

            enemy = state.planet.enemy
            control_pct = pct(state.planet.control)

            def op_line(op_type: OperationTypeId) -> str:
                cfg = state.rules.operation_types.get(op_type.value)
                if not cfg:
                    return op_type.value.upper()
                dmin, dmax = cfg.duration_range
                return f"{cfg.name.upper()} ({dmin}-{dmax}d)"

            line(f"SECTOR BRIEFING: {target.value.upper()}", "title")
            line(
                f"STATUS: {status_label(status)} | TYPE: {obj_type} | DIFF x{difficulty:.2f}",
                "muted",
            )
            line(
                f"ENEMY: {enemy.strength_min:.1f}-{enemy.strength_max:.1f} "
                f"({int(enemy.confidence * 100)}% conf) | "
                f"FORT {enemy.fortification:.2f} | REINF {enemy.reinforcement_rate:.2f} | "
                f"CONTROL {control_pct}%",
                "muted",
            )
            line("")
            line("ON-SITE DETAILS", "title")
            line(description, "muted")
            line("")
            line("SELECT OPERATION TYPE", "title")
            action("sector-raid", f"[A] {op_line(OperationTypeId.RAID)}")
            action("sector-campaign", f"[B] {op_line(OperationTypeId.CAMPAIGN)}")
            action("sector-siege", f"[C] {op_line(OperationTypeId.SIEGE)}")
            action("btn-sector-back", "[Q] BACK", "muted")

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
            action("optype-raid", "[A] RAID (Fast / Low Supply)")
            action("optype-campaign", "[B] CAMPAIGN (Balanced)")
            action("optype-siege", "[C] SIEGE (Slow / Safe)")
            action("btn-cancel", "[Q] CANCEL", "muted")

    elif mode == "plan:axis":
        line("PHASE 1: CONTACT & SHAPING - APPROACH AXIS", "title")
        action("axis-direct", "[A] DIRECT (Fast, High Risk)")
        action("axis-flank", "[B] FLANK (Slow, Low Risk)")
        action("axis-dispersed", "[C] DISPERSED (High Variance)")
        action("axis-stealth", "[D] STEALTH (Minimal Contact)")

    elif mode == "plan:prep":
        line("PHASE 1: CONTACT & SHAPING - FIRE SUPPORT", "title")
        action("prep-conserve", "[A] CONSERVE AMMO (No Bonus)")
        action("prep-preparatory", "[B] PREPARATORY BOMBARDMENT (+Effect, -Ammo)")

    elif mode == "plan:posture":
        line("PHASE 2: MAIN ENGAGEMENT - POSTURE", "title")
        action("posture-shock", "[A] SHOCK (High Impact, High Casualty)")
        action("posture-methodical", "[B] METHODICAL (Balanced)")
        action("posture-siege", "[C] SIEGE (Slow, Safe)")
        action("posture-feint", "[D] FEINT (Distraction)")

    elif mode == "plan:risk":
        line("PHASE 2: MAIN ENGAGEMENT - RISK TOLERANCE", "title")
        action("risk-low", "[A] LOW (Minimize Losses)")
        action("risk-med", "[B] MEDIUM (Standard Doctrine)")
        action("risk-high", "[C] HIGH (Accept Casualties for Speed)")

    elif mode == "plan:exploit":
        line("PHASE 3: EXPLOIT & CONSOLIDATE - FOCUS", "title")
        action("exploit-push", "[A] PUSH (Maximize Gains)")
        action("exploit-secure", "[B] SECURE (Defend Gains)")

    elif mode == "plan:end":
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
                action("prod-item-inf", "[A] INFANTRY (SQUADS)")
                action("prod-item-walkers", "[B] WALKERS")
                action("prod-item-support", "[C] SUPPORT")
            action("prod-back-category", "[Q] BACK", "muted")

    elif mode == "production:quantity":
        if controller.prod_job_type is None:
            line("SELECT AN ITEM FIRST.", "alert")
            action("prod-back-category", "[Q] BACK", "muted")
        else:
            job_label = controller.prod_job_type.value.upper()
            quantity_line = f"{controller.prod_quantity}"
            if controller.prod_job_type == ProductionJobType.INFANTRY:
                quantity_line += f" squads ({fmt_int(controller.prod_quantity * SQUAD_SIZE)} troops)"
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
            quantity_line = f"{controller.prod_quantity}"
            if controller.prod_job_type == ProductionJobType.INFANTRY:
                quantity_line += f" squads ({fmt_int(controller.prod_quantity * SQUAD_SIZE)} troops)"
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
            inf_4 = f"{fmt_int(4 * SQUAD_SIZE)} troops"
            line(f"SHIPMENT PACKAGE {origin.value} -> {destination.value}", "title")
            action("ship-mixed-1", "[A] MIXED (A40 F30 M15)")
            action("ship-ammo-1", "[B] AMMO RUN (A60)")
            action("ship-fuel-1", "[C] FUEL RUN (F50)")
            action("ship-med-1", "[D] MED/SPARES (M30)")
            action("ship-inf-1", f"[E] INFANTRY (I4 / {inf_4})")
            action("ship-walk-1", "[F] WALKERS (W2)")
            action("ship-sup-1", "[G] SUPPORT (S3)")
            action("ship-units-1", f"[H] MIXED UNITS (I4/{inf_4} W1 S2)")
            action("btn-logistics-back", "[Q] BACK", "muted")

    elif mode == "aar":
        aar = state.last_aar
        if aar is None:
            line("NO AFTER ACTION REPORT AVAILABLE.", "muted")
            action("btn-ack", "[ACKNOWLEDGE]", "accent")
        else:
            outcome = aar.outcome
            outcome_kind = "success" if ("CAPTURED" in outcome or "RAIDED" in outcome) else "failure"
            key_factor = aar.top_factors[0].why if aar.top_factors else "N/A"
            actions.append({"id": "btn-ack", "label": "[ACKNOWLEDGE]", "tone": "accent"})
            return {
                "mode": mode,
                "message": controller.message,
                "message_kind": controller.message_kind,
                "lines": [],
                "actions": actions,
                "aar": {
                    "outcome": outcome,
                    "outcome_kind": outcome_kind,
                    "summary": f"TARGET: {aar.target.value} | LOSSES: {aar.losses} | DAYS: {aar.days}",
                    "key_factor": key_factor,
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
    }


PANEL_SPECS: dict[str, PanelSpec] = {
    "header": PanelSpec(template="panels/header.html", builder=header_vm),
    "map": PanelSpec(template="panels/situation_map.html", builder=situation_map_vm),
    "enemy": PanelSpec(template="panels/enemy_intel.html", builder=enemy_intel_vm),
    "taskforce": PanelSpec(template="panels/task_force.html", builder=task_force_vm),
    "production": PanelSpec(template="panels/production.html", builder=production_vm),
    "logistics": PanelSpec(template="panels/logistics.html", builder=logistics_vm),
    "console": PanelSpec(template="panels/console.html", builder=console_vm),
}
