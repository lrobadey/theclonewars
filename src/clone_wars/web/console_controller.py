from __future__ import annotations

from dataclasses import dataclass, field

from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.ops import OperationPlan, OperationTarget, OperationTypeId
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.state import GameState
from clone_wars.engine.types import SQUAD_SIZE, Supplies, UnitStock


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

    def _set_message(self, text: str | None, kind: str = "info") -> None:
        self.message = text
        self.message_kind = kind

    def sync_with_state(self, state: GameState) -> None:
        if state.last_aar is not None and self.mode != "aar":
            self.mode = "aar"
        if self.mode == "aar" and state.last_aar is None:
            self.mode = "menu"
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
        if state.operation is not None:
            self._set_message("OPERATION ALREADY ACTIVE", "error")
            self.mode = "menu"
            return
        self.target = target
        self.op_type = OperationTypeId.CAMPAIGN
        self.mode = "sector"

    def dispatch(self, action_id: str, payload: dict[str, str], state: GameState) -> None:
        if not action_id:
            return

        if action_id == "btn-plan":
            if state.operation is not None:
                self._set_message("OPERATION ALREADY ACTIVE", "error")
                self.mode = "menu"
            else:
                self.mode = "plan:target"
        elif action_id == "btn-next":
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

        elif action_id.startswith("sector-"):
            op_map = {
                "sector-raid": OperationTypeId.RAID,
                "sector-campaign": OperationTypeId.CAMPAIGN,
                "sector-siege": OperationTypeId.SIEGE,
            }
            chosen = op_map.get(action_id)
            if chosen is None or self.target is None:
                return
            self.op_type = chosen
            self.mode = "plan:axis"

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
                return
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
                if state.operation is not None:
                    self._set_message("OPERATION ALREADY ACTIVE", "error")
                    self.mode = "menu"
                    self.plan_draft.clear()
                    self.target = None
                    self.op_type = OperationTypeId.CAMPAIGN
                    self.sync_with_state(state)
                    return
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
                return
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
                return
            if action_id == "prod-qty-next":
                if self.prod_quantity <= 0:
                    self._set_message("SET A QUANTITY BEFORE CONTINUING", "error")
                    return
                self.mode = "production:stop"
                return
            delta = delta_map.get(action_id)
            if delta is None:
                return
            self.prod_quantity = max(0, self.prod_quantity + delta)

        elif action_id.startswith("prod-stop-"):
            if self.prod_job_type is None:
                return
            if self.prod_quantity <= 0:
                self._set_message("SET A QUANTITY BEFORE QUEUING", "error")
                self.mode = "production:quantity"
                return
            stop_map = {
                "prod-stop-core": DepotNode.CORE,
                "prod-stop-mid": DepotNode.MID,
                "prod-stop-front": DepotNode.FRONT,
            }
            stop_at = stop_map.get(action_id)
            if stop_at is None:
                return
            state.production.queue_job(self.prod_job_type, self.prod_quantity, stop_at)
            qty_line = f"{self.prod_quantity}"
            if self.prod_job_type == ProductionJobType.INFANTRY:
                qty_line = f"{qty_line} squads ({self.prod_quantity * SQUAD_SIZE} troops)"
            self._set_message(
                f"QUEUED {self.prod_job_type.value.upper()} x{qty_line} -> {stop_at.value.upper()}",
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
                "ship-inf-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(4, 0, 0)),
                "ship-walk-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(0, 2, 0)),
                "ship-sup-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(0, 0, 3)),
                "ship-units-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(4, 1, 2)),
            }
            package = package_map.get(action_id)
            if package and self.pending_route:
                supplies, units = package
                origin, destination = self.pending_route
                try:
                    state.logistics.create_shipment(origin, destination, supplies, units, state.rng)
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
