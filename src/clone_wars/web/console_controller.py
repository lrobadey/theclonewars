from __future__ import annotations

from dataclasses import dataclass, field

from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.ops import OperationPlan, OperationTarget, OperationTypeId
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.state import GameState
from clone_wars.engine.types import Supplies, UnitStock


def _ui_dirty_for_action(action_id: str) -> set[str]:
    """
    Returns the set of web dashboard panels that should be re-rendered after an action.

    The goal is to avoid re-rendering the full UI for every click; most actions only
    affect the console, while some also affect specific panels.
    """
    dirty: set[str] = {"console"}

    # Selecting a node changes map selection + console briefing.
    if action_id.startswith("map-"):
        dirty.add("map")

    # Production/logistics "sub-modes" render controls inside those panels.
    if action_id.startswith("prod-") or action_id == "btn-production":
        dirty.add("production")
    if action_id.startswith("route-") or action_id.startswith("ship-") or action_id == "btn-logistics":
        dirty.add("logistics")

    # Advancing the day can change almost everything the dashboard displays.
    if action_id == "btn-next":
        dirty.update({"header", "map", "enemy", "taskforce", "production", "logistics"})

    if action_id in {"btn-raid", "btn-raid-tick", "btn-raid-auto"}:
        dirty.update({"map", "enemy", "taskforce"})
    if action_id == "btn-raid-resolve":
        dirty.update({"map", "enemy", "taskforce"})

    # AAR acknowledgement returns to menu; console-only.
    return dirty


@dataclass
class ConsoleController:
    mode: str = "menu"
    target: OperationTarget | None = None
    op_type: OperationTypeId = OperationTypeId.CAMPAIGN
    plan_draft: dict[str, str] = field(default_factory=dict)
    pending_route: tuple[DepotNode, DepotNode] | None = None
    prod_category: str | None = None
    prod_job_type: ProductionJobType | None = None
    prod_quantity: int = 0
    message: str | None = None
    message_kind: str = "info"
    raid_auto: bool = False

    def _set_message(self, text: str | None, kind: str = "info") -> None:
        self.message = text
        self.message_kind = kind

    def sync_with_state(self, state: GameState) -> None:
        if state.last_aar is not None and self.mode != "aar":
            self.mode = "aar"
        if state.raid_session is not None and self.mode != "raid":
            self.mode = "raid"
        if self.mode == "aar" and state.last_aar is None:
            self.mode = "menu"
        if self.mode == "raid" and state.raid_session is None and state.last_aar is None:
            self.mode = "menu"
        if state.raid_session is None:
            self.raid_auto = False
        if self.mode == "logistics:package" and self.pending_route is None:
            self.mode = "logistics"
        if self.mode == "sector" and self.target is None:
            self.mode = "menu"
        if self.mode.startswith("plan:") and self.target is None and self.mode != "plan:target":
            self.mode = "plan:target"
        if self.mode == "production:item" and self.prod_category is None:
            self.mode = "production"
        if self.mode in {"production:quantity", "production:stop"} and self.prod_job_type is None:
            self.mode = "production"

    def open_sector(self, target: OperationTarget, state: GameState) -> None:
        if state.operation is not None or state.raid_session is not None:
            self._set_message("OPERATION ALREADY ACTIVE", "error")
            self.mode = "menu"
            return
        self.target = target
        self.op_type = OperationTypeId.CAMPAIGN
        self.mode = "sector"

    def dispatch(self, action_id: str, payload: dict[str, str], state: GameState) -> set[str]:
        if not action_id:
            return {"console"}

        dirty = _ui_dirty_for_action(action_id)

        if action_id == "btn-plan":
            self._set_message("PHASED OPS DEPRECATED — USE RAID", "error")
            self.mode = "menu"
        elif action_id == "btn-next":
            if state.raid_session is not None:
                self._set_message("RAID IN PROGRESS", "error")
                self.mode = "raid"
                return dirty
            state.advance_day()
            self._set_message("DAY ADVANCED", "info")
        elif action_id == "btn-sector-back":
            self.target = None
            self.op_type = OperationTypeId.CAMPAIGN
            self.mode = "menu"
        elif action_id == "btn-cancel":
            self.pending_route = None
            if self.mode.startswith("plan:"):
                self.plan_draft.clear()
                self.target = None
                self.op_type = OperationTypeId.CAMPAIGN
            self.prod_category = None
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "menu"
        elif action_id == "btn-ack":
            state.last_aar = None
            self.mode = "menu"
            self.raid_auto = False
        elif action_id == "btn-production":
            self.prod_category = None
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "production"
        elif action_id == "btn-logistics":
            self.mode = "logistics"

        elif action_id.startswith("map-"):
            target_map = {
                "map-foundry": OperationTarget.FOUNDRY,
                "map-comms": OperationTarget.COMMS,
                "map-power": OperationTarget.POWER,
            }
            target = target_map.get(action_id)
            if target is not None:
                self.open_sector(target, state)

        elif action_id == "btn-raid":
            if self.target is None:
                self._set_message("NO TARGET SELECTED", "error")
                self.mode = "menu"
            else:
                try:
                    self.raid_auto = False
                    state.start_raid(self.target)
                except RuntimeError as exc:
                    self._set_message(str(exc).upper(), "error")
                    self.mode = "menu"
                else:
                    self._set_message("RAID STARTED", "accent")
                    self.mode = "raid"

        elif action_id == "btn-raid-tick":
            try:
                state.advance_raid_tick()
            except RuntimeError as exc:
                self._set_message(str(exc).upper(), "error")
                self.mode = "menu"
            else:
                if state.raid_session is None and state.last_aar is not None:
                    self.mode = "aar"
                else:
                    self.mode = "raid"

        elif action_id == "btn-raid-resolve":
            try:
                self.raid_auto = False
                state.resolve_active_raid()
            except RuntimeError as exc:
                self._set_message(str(exc).upper(), "error")
                self.mode = "menu"
            else:
                self._set_message("RAID RESOLVED", "accent")
                self.mode = "aar"
        elif action_id == "btn-raid-auto":
            if state.raid_session is None:
                self._set_message("NO ACTIVE RAID", "error")
                self.mode = "menu"
            else:
                self.raid_auto = not self.raid_auto
                self._set_message("AUTO ADVANCE ON" if self.raid_auto else "AUTO ADVANCE OFF", "info")
                self.mode = "raid"

        elif action_id.startswith("sector-"):
            op_map = {
                "sector-raid": OperationTypeId.RAID,
                "sector-campaign": OperationTypeId.CAMPAIGN,
                "sector-siege": OperationTypeId.SIEGE,
            }
            chosen = op_map.get(action_id)
            if chosen is None or self.target is None:
                return dirty
            if chosen != OperationTypeId.RAID:
                self._set_message("ONLY RAID AVAILABLE", "error")
                self.mode = "sector"
            else:
                try:
                    self.raid_auto = False
                    state.start_raid(self.target)
                except RuntimeError as exc:
                    self._set_message(str(exc).upper(), "error")
                    self.mode = "menu"
                else:
                    self._set_message("RAID STARTED", "accent")
                    self.mode = "raid"

        elif action_id.startswith("target-"):
            t_map = {
                "target-foundry": OperationTarget.FOUNDRY,
                "target-comms": OperationTarget.COMMS,
                "target-power": OperationTarget.POWER,
            }
            self.target = t_map.get(action_id)
            self.mode = "plan:type"

        elif action_id.startswith("optype-"):
            op_map = {
                "optype-raid": OperationTypeId.RAID,
                "optype-campaign": OperationTypeId.CAMPAIGN,
                "optype-siege": OperationTypeId.SIEGE,
            }
            chosen = op_map.get(action_id)
            if chosen is None:
                return dirty
            self.op_type = chosen
            self.mode = "plan:axis"

        elif action_id.startswith("axis-"):
            self.plan_draft["approach_axis"] = action_id.split("-")[1]
            self.mode = "plan:prep"

        elif action_id.startswith("prep-"):
            self.plan_draft["fire_support_prep"] = action_id.split("-")[1]
            self.mode = "plan:posture"

        elif action_id.startswith("posture-"):
            self.plan_draft["engagement_posture"] = action_id.split("-")[1]
            self.mode = "plan:risk"

        elif action_id.startswith("risk-"):
            self.plan_draft["risk_tolerance"] = action_id.split("-")[1]
            self.mode = "plan:exploit"

        elif action_id.startswith("exploit-"):
            self.plan_draft["exploit_vs_secure"] = action_id.split("-")[1]
            self.mode = "plan:end"

        elif action_id.startswith("end-"):
            self.plan_draft["end_state"] = action_id.split("-")[1]
            if self.target:
                if state.operation is not None or state.raid_session is not None:
                    self._set_message("OPERATION ALREADY ACTIVE", "error")
                    self.mode = "menu"
                    self.plan_draft.clear()
                    self.target = None
                    self.op_type = OperationTypeId.CAMPAIGN
                    self.sync_with_state(state)
                    return dirty
                plan = OperationPlan(
                    target=self.target,
                    approach_axis=self.plan_draft["approach_axis"],
                    fire_support_prep=self.plan_draft["fire_support_prep"],
                    engagement_posture=self.plan_draft["engagement_posture"],
                    risk_tolerance=self.plan_draft["risk_tolerance"],
                    exploit_vs_secure=self.plan_draft["exploit_vs_secure"],
                    end_state=self.plan_draft["end_state"],
                    op_type=self.op_type,
                )
                self._set_message("OPERATION LAUNCHED", "accent")
                self.mode = "menu"
                self.plan_draft.clear()
                self.target = None
                self.op_type = OperationTypeId.CAMPAIGN
                state.start_operation(plan)

        elif action_id == "prod-upgrade-factory":
            try:
                state.production.add_factory()
            except ValueError as exc:
                self._set_message(str(exc).upper(), "error")
                return dirty
            self._set_message("FACTORY UPGRADE COMPLETE (+1 SLOT)", "accent")
            self.mode = "menu"

        elif action_id.startswith("prod-cat-"):
            self.prod_category = "supplies" if action_id == "prod-cat-supplies" else "army"
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "production:item"

        elif action_id.startswith("prod-item-"):
            job_map = {
                "prod-item-ammo": ProductionJobType.AMMO,
                "prod-item-fuel": ProductionJobType.FUEL,
                "prod-item-med": ProductionJobType.MED_SPARES,
                "prod-item-inf": ProductionJobType.INFANTRY,
                "prod-item-walkers": ProductionJobType.WALKERS,
                "prod-item-support": ProductionJobType.SUPPORT,
            }
            job_type = job_map.get(action_id)
            if job_type is None:
                return dirty
            self.prod_job_type = job_type
            self.prod_quantity = 0
            self.mode = "production:quantity"

        elif action_id.startswith("prod-qty-"):
            delta_map = {
                "prod-qty-minus-50": -50,
                "prod-qty-minus-10": -10,
                "prod-qty-minus-1": -1,
                "prod-qty-plus-1": 1,
                "prod-qty-plus-10": 10,
                "prod-qty-plus-50": 50,
            }
            if action_id == "prod-qty-reset":
                self.prod_quantity = 0
                return dirty
            if action_id == "prod-qty-next":
                if self.prod_quantity <= 0:
                    self._set_message("SET A QUANTITY BEFORE CONTINUING", "error")
                    return dirty
                self.mode = "production:stop"
                return dirty
            delta = delta_map.get(action_id)
            if delta is None:
                return dirty
            self.prod_quantity = max(0, self.prod_quantity + delta)

        elif action_id.startswith("prod-stop-"):
            if self.prod_job_type is None:
                return dirty
            if self.prod_quantity <= 0:
                self._set_message("SET A QUANTITY BEFORE QUEUING", "error")
                self.mode = "production:quantity"
                return dirty
            stop_map = {
                "prod-stop-core": DepotNode.CORE,
                "prod-stop-mid": DepotNode.MID,
                "prod-stop-front": DepotNode.FRONT,
            }
            stop_at = stop_map.get(action_id)
            if stop_at is None:
                return dirty
            state.production.queue_job(self.prod_job_type, self.prod_quantity, stop_at)
            self._set_message(
                f"QUEUED {self.prod_job_type.value.upper()} x{self.prod_quantity:,} -> {stop_at.value.upper()}",
                "info",
            )
            self.prod_category = None
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "menu"

        elif action_id == "prod-back-category":
            self.prod_category = None
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "production"

        elif action_id == "prod-back-item":
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "production:item"

        elif action_id == "prod-back-qty":
            self.mode = "production:quantity"

        elif action_id.startswith("route-"):
            route_map = {
                "route-core-mid": (DepotNode.CORE, DepotNode.MID),
                "route-mid-front": (DepotNode.MID, DepotNode.FRONT),
            }
            route = route_map.get(action_id)
            if route:
                self.pending_route = route
                self.mode = "logistics:package"

        elif action_id.startswith("ship-"):
            package_map = {
                "ship-mixed-1": (Supplies(ammo=40, fuel=30, med_spares=15), UnitStock(0, 0, 0)),
                "ship-ammo-1": (Supplies(ammo=60, fuel=0, med_spares=0), UnitStock(0, 0, 0)),
                "ship-fuel-1": (Supplies(ammo=0, fuel=50, med_spares=0), UnitStock(0, 0, 0)),
                "ship-med-1": (Supplies(ammo=0, fuel=0, med_spares=30), UnitStock(0, 0, 0)),
                "ship-inf-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(80, 0, 0)),
                "ship-walk-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(0, 2, 0)),
                "ship-sup-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(0, 0, 3)),
                "ship-units-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(80, 1, 2)),
            }
            package = package_map.get(action_id)
            if package and self.pending_route:
                supplies, units = package
                origin, destination = self.pending_route
                try:
                    state.logistics_service.create_shipment(state.logistics, origin, destination, supplies, units, state.rng)
                except ValueError as exc:
                    self._set_message(str(exc), "error")
                    self.mode = "logistics"
                else:
                    self._set_message(
                        f"SHIPMENT DISPATCHED: {origin.value} -> {destination.value}",
                        "info",
                    )
                    self.pending_route = None
                    self.mode = "menu"

        elif action_id == "btn-logistics-back":
            self.pending_route = None
            self.mode = "logistics"

        else:
            self._set_message(f"UNKNOWN ACTION: {action_id}", "error")

        self.sync_with_state(state)
        return dirty
