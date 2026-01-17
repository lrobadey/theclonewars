from __future__ import annotations

from typing import cast

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static
from textual.worker import Worker

from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.ops import OperationPlan, OperationTarget, OperationTypeId
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.state import AfterActionReport, GameState
from clone_wars.engine.types import ObjectiveStatus, SQUAD_SIZE, Supplies, UnitStock


def _fmt_int(n: int) -> str:
    return f"{n:,}"


class CommandConsole(Widget):
    """
    The state-machine console that handles game flow.
    It sits at the bottom and changes its content based on 'mode'.
    """

    # Modes: "menu", "sector", "plan:target", "plan:type", "plan:axis", "plan:prep", "plan:posture",
    #        "plan:risk", "plan:exploit", "plan:end",
    #        "production", "production:item", "production:quantity", "production:stop",
    #        "logistics", "logistics:package", "executing", "aar"
    mode = reactive("menu")

    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = state
        self._plan_draft: dict[str, str] = {}
        self._target: OperationTarget | None = None
        self._op_type: OperationTypeId = OperationTypeId.CAMPAIGN
        self._pending_route: tuple[DepotNode, DepotNode] | None = None
        self._prod_category: str | None = None
        self._prod_job_type: ProductionJobType | None = None
        self._prod_quantity: int = 0
        self._message: str | None = None
        self._last_content_key: str = ""
        self._refresh_worker: Worker[None] | None = None

    def compose(self) -> ComposeResult:
        yield Vertical(id="console-content")

    def on_mount(self) -> None:
        self._request_refresh()

    def update_view(self) -> None:
        """Safe entry point for external updates. Only triggers mode changes or guarded refreshes."""
        if self.state.last_aar is not None and self.mode != "aar":
            self.mode = "aar"
        elif self.mode in {"menu", "sector"}:
            self._request_refresh()

    @property
    def selected_target(self) -> OperationTarget | None:
        return self._target

    def open_sector(self, target: OperationTarget) -> None:
        """Open a mission-select / sector briefing for the clicked objective."""
        if self.state.operation is not None:
            self._message = "[#ff3b3b]OPERATION ALREADY ACTIVE[/]"
            self.mode = "menu"
            return
        old_mode = self.mode
        self._target = target
        self._op_type = OperationTypeId.CAMPAIGN
        self.mode = "sector"
        if old_mode == "sector":
            self._request_refresh()

    def start_plan_with_target(self, target: OperationTarget) -> None:
        if self.state.operation is not None:
            self._message = "[#ff3b3b]OPERATION ALREADY ACTIVE[/]"
            self.mode = "menu"
            return
        old_mode = self.mode
        self._target = target
        self._op_type = OperationTypeId.CAMPAIGN
        self.mode = "plan:type"
        if old_mode == "plan:type":
            self._request_refresh()

    def _objective_id_for_target(self, target: OperationTarget) -> str:
        match target:
            case OperationTarget.FOUNDRY:
                return "foundry"
            case OperationTarget.COMMS:
                return "comms"
            case OperationTarget.POWER:
                return "power"

    def _objective_status_for_target(self, target: OperationTarget) -> ObjectiveStatus:
        obj = self.state.planet.objectives
        match target:
            case OperationTarget.FOUNDRY:
                return obj.foundry
            case OperationTarget.COMMS:
                return obj.comms
            case OperationTarget.POWER:
                return obj.power

    def _objective_status_label(self, status: ObjectiveStatus) -> tuple[str, str]:
        match status:
            case ObjectiveStatus.ENEMY:
                return ("ENEMY HELD", "#ff3b3b")
            case ObjectiveStatus.CONTESTED:
                return ("CONTESTED", "#f0b429")
            case ObjectiveStatus.SECURED:
                return ("FRIENDLY", "#e5e7eb")

    def watch_mode(self, mode: str) -> None:
        self._last_content_key = ""
        self._request_refresh()

    def _request_refresh(self) -> None:
        if not self.is_attached:
            return
        self._refresh_worker = self.run_worker(
            self._refresh_content(),
            name="console-refresh",
            group="console-refresh",
            exclusive=True,
            exit_on_error=False,
        )

    async def _refresh_content(self) -> None:
        """Clear and rebuild the console content based on current mode."""
        if self.mode == "menu" and self.state.last_aar is not None:
            self.mode = "aar"
            return
        if self.mode == "logistics:package" and not self._pending_route:
            self.mode = "logistics"
            return
        if self.mode == "aar" and self.state.last_aar is None:
            self.mode = "menu"
            return

        op_day = self.state.operation.day_in_operation if self.state.operation else -1
        content_key = (
            f"{self.mode}:{self.state.operation is not None}:{op_day}:{self.state.last_aar is not None}:"
            f"{self._target}:{self._op_type.value}:{self._message}:"
            f"{self._prod_category}:{self._prod_job_type}:{self._prod_quantity}"
        )

        if content_key == self._last_content_key:
            return

        container = self.query_one("#console-content")
        await container.remove_children()

        if self._message:
            container.mount(Static(self._message, markup=True))

        # --- MAIN MENU ---
        if self.mode == "menu":
            if self.state.operation is not None:
                op = self.state.operation
                container.mount(
                    Static(
                        f"[bold #ff3b3b]ALERT: OPERATION ACTIVE - {op.target.value.upper()}[/]\n"
                        f"DAY {op.day_in_operation} OF {op.estimated_days}  |  STATUS: IN PROGRESS",
                        markup=True,
                    ),
                    Static("waiting for daily reports... (press 'n' or click button to advance day)"),
                    Button("[N] NEXT DAY", id="btn-next"),
                )
            else:
                container.mount(
                    Static("[bold]COMMAND LINK ESTABLISHED. AWAITING ORDERS.[/]", markup=True),
                    Button("[1] PLAN OFFENSIVE", id="btn-plan"),
                    Button("[2] PRODUCTION", id="btn-production"),
                    Button("[3] LOGISTICS", id="btn-logistics"),
                    Button("[4] NEXT DAY", id="btn-next"),
                )

        # --- SECTOR DETAIL / MISSION SELECT ---
        elif self.mode == "sector":
            if self._target is None:
                self.mode = "menu"
                return

            target = self._target
            status = self._objective_status_for_target(target)
            status_label, status_color = self._objective_status_label(status)

            obj_id = self._objective_id_for_target(target)
            obj_def = self.state.rules.objectives.get(obj_id)
            obj_type = obj_def.type.upper() if obj_def else "UNKNOWN"
            difficulty = obj_def.base_difficulty if obj_def else 1.0
            description = (obj_def.description if obj_def else "").strip()

            enemy = self.state.planet.enemy
            control_pct = int(max(0.0, min(1.0, self.state.planet.control)) * 100)

            def _op_line(op_type: OperationTypeId) -> str:
                cfg = self.state.rules.operation_types.get(op_type.value)
                if not cfg:
                    return op_type.value.upper()
                dmin, dmax = cfg.duration_range
                return f"{cfg.name.upper()} ({dmin}–{dmax}d)"

            container.mount(
                Static(f"[bold]SECTOR BRIEFING:[/] {target.value.upper()}", markup=True),
                Static(
                    f"STATUS: [{status_color}]{status_label}[/{status_color}]  |  "
                    f"TYPE: {obj_type}  |  DIFFICULTY: x{difficulty:.2f}",
                    markup=True,
                ),
                Static(
                    f"ENEMY: {enemy.strength_min:.1f}–{enemy.strength_max:.1f} "
                    f"({int(enemy.confidence * 100)}% conf)  |  "
                    f"FORT: {enemy.fortification:.2f}  |  REINF: {enemy.reinforcement_rate:.2f}  |  "
                    f"CONTROL: {control_pct}%",
                ),
                Static(""),
                Static("[bold]ON-SITE DETAILS[/]", markup=True),
                Static(description or "No details available."),
                Static(""),
                Static("[bold]SELECT OPERATION TYPE[/]", markup=True),
                Button(f"[A] {_op_line(OperationTypeId.RAID)}", id="sector-raid"),
                Button(f"[B] {_op_line(OperationTypeId.CAMPAIGN)}", id="sector-campaign"),
                Button(f"[C] {_op_line(OperationTypeId.SIEGE)}", id="sector-siege"),
                Button("[Q] BACK", id="btn-sector-back"),
            )

        # --- PLANNING FLOW ---
        elif self.mode == "plan:target":
            container.mount(
                Static("[bold]PHASE 0: SELECT TARGET SECTOR[/]", markup=True),
                Button("[A] DROID FOUNDRY (Primary Ind.)", id="target-foundry"),
                Button("[B] COMM ARRAY (Intel/C2)", id="target-comms"),
                Button("[C] POWER PLANT (Infrastructure)", id="target-power"),
                Button("[Q] CANCEL", id="btn-cancel"),
            )

        elif self.mode == "plan:type":
            if self._target is None:
                self.mode = "plan:target"
                return
            container.mount(
                Static("[bold]PHASE 0: SELECT OPERATION TYPE[/]", markup=True),
                Static(f"TARGET: {self._target.value}"),
                Button("[A] RAID (Fast / Low Supply)", id="optype-raid"),
                Button("[B] CAMPAIGN (Balanced)", id="optype-campaign"),
                Button("[C] SIEGE (Slow / Safe)", id="optype-siege"),
                Button("[Q] CANCEL", id="btn-cancel"),
            )

        elif self.mode == "plan:axis":
            container.mount(
                Static("[bold]PHASE 1: CONTACT & SHAPING - APPROACH AXIS[/]", markup=True),
                Button("[A] DIRECT (Fast, High Risk)", id="axis-direct"),
                Button("[B] FLANK (Slow, Low Risk)", id="axis-flank"),
                Button("[C] DISPERSED (High Variance)", id="axis-dispersed"),
                Button("[D] STEALTH (Minimal Contact)", id="axis-stealth"),
            )

        elif self.mode == "plan:prep":
            container.mount(
                Static("[bold]PHASE 1: CONTACT & SHAPING - FIRE SUPPORT[/]", markup=True),
                Button("[A] CONSERVE AMMO (No Bonus)", id="prep-conserve"),
                Button("[B] PREPARATORY BOMBARDMENT (+Effect, -Ammo)", id="prep-preparatory"),
            )

        elif self.mode == "plan:posture":
            container.mount(
                Static("[bold]PHASE 2: MAIN ENGAGEMENT - POSTURE[/]", markup=True),
                Button("[A] SHOCK (High Impact, High Casualty)", id="posture-shock"),
                Button("[B] METHODICAL (Balanced)", id="posture-methodical"),
                Button("[C] SIEGE (Slow, Safe)", id="posture-siege"),
                Button("[D] FEINT (Distraction)", id="posture-feint"),
            )

        elif self.mode == "plan:risk":
            container.mount(
                Static("[bold]PHASE 2: MAIN ENGAGEMENT - RISK TOLERANCE[/]", markup=True),
                Button("[A] LOW (Minimize Losses)", id="risk-low"),
                Button("[B] MEDIUM (Standard Doctrine)", id="risk-med"),
                Button("[C] HIGH (Accept Casualties for Speed)", id="risk-high"),
            )

        elif self.mode == "plan:exploit":
            container.mount(
                Static("[bold]PHASE 3: EXPLOIT & CONSOLIDATE - FOCUS[/]", markup=True),
                Button("[A] PUSH (Maximize Gains)", id="exploit-push"),
                Button("[B] SECURE (Defend Gains)", id="exploit-secure"),
            )

        elif self.mode == "plan:end":
            container.mount(
                Static("[bold]PHASE 3: EXPLOIT & CONSOLIDATE - END STATE[/]", markup=True),
                Button("[A] CAPTURE (Hold Sector)", id="end-capture"),
                Button("[B] RAID (Damage & Retreat)", id="end-raid"),
                Button("[C] DESTROY (Scorched Earth)", id="end-destroy"),
                Button("[Q] CANCEL", id="btn-cancel"),
            )

        # --- PRODUCTION ---
        elif self.mode == "production":
            container.mount(
                Static("[bold]PRODUCTION COMMAND[/]", markup=True),
                Static("SELECT CATEGORY:"),
                Button("[A] SUPPLIES", id="prod-cat-supplies"),
                Button("[B] ARMY", id="prod-cat-army"),
            )
            if self.state.production.can_add_factory():
                container.mount(Button("[C] UPGRADE FACTORY (+1 SLOT)", id="prod-upgrade-factory"))
            container.mount(Button("[Q] BACK", id="btn-cancel"))

        elif self.mode == "production:item":
            if self._prod_category is None:
                self.mode = "production"
                return
            title = self._prod_category.upper()
            container.mount(
                Static(f"[bold]PRODUCTION - {title}[/]", markup=True),
                Static("SELECT ITEM:"),
            )
            if self._prod_category == "supplies":
                container.mount(
                    Button("[A] AMMO", id="prod-item-ammo"),
                    Button("[B] FUEL", id="prod-item-fuel"),
                    Button("[C] MED/SPARES", id="prod-item-med"),
                )
            else:
                container.mount(
                    Button("[A] INFANTRY (SQUADS)", id="prod-item-inf"),
                    Button("[B] WALKERS", id="prod-item-walkers"),
                    Button("[C] SUPPORT", id="prod-item-support"),
                )
            container.mount(Button("[Q] BACK", id="prod-back-category"))

        elif self.mode == "production:quantity":
            if self._prod_job_type is None:
                self.mode = "production"
                return
            job_label = self._prod_job_type.value.upper()
            quantity_line = f"{self._prod_quantity}"
            if self._prod_job_type == ProductionJobType.INFANTRY:
                quantity_line += f" squads ({_fmt_int(self._prod_quantity * SQUAD_SIZE)} troops)"
            container.mount(
                Static("[bold]PRODUCTION - QUANTITY[/]", markup=True),
                Static(f"ITEM: {job_label}"),
                Static(f"QUANTITY: {quantity_line}"),
                Button("[-50]", id="prod-qty-minus-50"),
                Button("[-10]", id="prod-qty-minus-10"),
                Button("[-1]", id="prod-qty-minus-1"),
                Button("[+1]", id="prod-qty-plus-1"),
                Button("[+10]", id="prod-qty-plus-10"),
                Button("[+50]", id="prod-qty-plus-50"),
                Button("[RESET]", id="prod-qty-reset"),
                Button("[NEXT] CHOOSE DEPOT", id="prod-qty-next"),
                Button("[Q] BACK", id="prod-back-item"),
            )

        elif self.mode == "production:stop":
            if self._prod_job_type is None:
                self.mode = "production"
                return
            job_label = self._prod_job_type.value.upper()
            quantity_line = f"{self._prod_quantity}"
            if self._prod_job_type == ProductionJobType.INFANTRY:
                quantity_line += f" squads ({_fmt_int(self._prod_quantity * SQUAD_SIZE)} troops)"
            container.mount(
                Static("[bold]PRODUCTION - DELIVER TO[/]", markup=True),
                Static(f"ITEM: {job_label}"),
                Static(f"QUANTITY: {quantity_line}"),
                Button("[A] CORE", id="prod-stop-core"),
                Button("[B] MID", id="prod-stop-mid"),
                Button("[C] FRONT", id="prod-stop-front"),
                Button("[Q] BACK", id="prod-back-qty"),
            )

        # --- LOGISTICS ---
        elif self.mode == "logistics":
            container.mount(
                Static("[bold]LOGISTICS COMMAND[/]", markup=True),
                Static("SELECT ROUTE TO CREATE SHIPMENT:"),
                Button("[A] CORE -> MID", id="route-core-mid"),
                Button("[B] MID -> FRONT", id="route-mid-front"),
                Button("[Q] BACK", id="btn-cancel"),
            )

        elif self.mode == "logistics:package":
            origin, destination = cast(tuple[DepotNode, DepotNode], self._pending_route)
            inf_4 = f"{4 * SQUAD_SIZE} troops"
            container.mount(
                Static(
                    f"[bold]SHIPMENT PACKAGE[/] {origin.value} -> {destination.value}",
                    markup=True,
                ),
                Button("[A] MIXED (A40 F30 M15)", id="ship-mixed-1"),
                Button("[B] AMMO RUN (A60)", id="ship-ammo-1"),
                Button("[C] FUEL RUN (F50)", id="ship-fuel-1"),
                Button("[D] MED/SPARES (M30)", id="ship-med-1"),
                Button(f"[E] INFANTRY (I4 / {inf_4})", id="ship-inf-1"),
                Button("[F] WALKERS (W2)", id="ship-walk-1"),
                Button("[G] SUPPORT (S3)", id="ship-sup-1"),
                Button(f"[H] MIXED UNITS (I4/{inf_4} W1 S2)", id="ship-units-1"),
                Button("[Q] BACK", id="btn-logistics-back"),
            )

        # --- AAR REPORT ---
        elif self.mode == "aar":
            aar = cast(AfterActionReport, self.state.last_aar)
            color = "#e5e7eb" if "CAPTURED" in aar.outcome or "RAIDED" in aar.outcome else "#ff3b3b"
            container.mount(
                Static(f"[bold {color}]MISSION COMPLETE: {aar.outcome}[/]", markup=True),
                Static(
                    f"TARGET: {aar.target.value} | LOSSES: {aar.losses} | DAYS: {aar.days}\n"
                    f"KEY FACTOR: {aar.top_factors[0].why if aar.top_factors else 'N/A'}"
                ),
                Button("[ACKNOWLEDGE]", id="btn-ack"),
            )

        self._last_content_key = content_key

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if not bid:
            return

        # Main Menu handlers
        if bid == "btn-plan":
            self.mode = "plan:target"
        elif bid == "btn-next":
            ran = await self.app.run_action("next_day")
            if not ran and hasattr(self.app, "action_next_day"):
                self.app.action_next_day()
            self._message = "[#a7adb5]DAY ADVANCED[/]"
            self._request_refresh()
        elif bid == "btn-sector-back":
            self._target = None
            self._op_type = OperationTypeId.CAMPAIGN
            self.mode = "menu"
        elif bid == "btn-cancel":
            self._pending_route = None
            if self.mode.startswith("plan:"):
                self._plan_draft.clear()
                self._target = None
                self._op_type = OperationTypeId.CAMPAIGN
            self._prod_category = None
            self._prod_job_type = None
            self._prod_quantity = 0
            self.mode = "menu"
        elif bid == "btn-ack":
            self.state.last_aar = None
            self.mode = "menu"
        elif bid == "btn-production":
            self._prod_category = None
            self._prod_job_type = None
            self._prod_quantity = 0
            self.mode = "production"
        elif bid == "btn-logistics":
            self.mode = "logistics"
        elif bid == "prod-upgrade-factory":
            try:
                self.state.production.add_factory()
            except ValueError as exc:
                self._message = f"[#ff3b3b]{exc}[/]"
            else:
                self._message = "[#a7adb5]FACTORY UPGRADE COMPLETE (+1 SLOT)[/]"
            self.mode = "menu"

        # Sector (mission select) handlers
        elif bid.startswith("sector-"):
            op_map = {
                "sector-raid": OperationTypeId.RAID,
                "sector-campaign": OperationTypeId.CAMPAIGN,
                "sector-siege": OperationTypeId.SIEGE,
            }
            chosen = op_map.get(bid)
            if chosen is None or self._target is None:
                return
            self._op_type = chosen
            self.mode = "plan:axis"

        # Planning Handlers
        elif bid.startswith("target-"):
            t_map = {
                "target-foundry": OperationTarget.FOUNDRY,
                "target-comms": OperationTarget.COMMS,
                "target-power": OperationTarget.POWER,
            }
            self._target = t_map.get(bid)
            self.mode = "plan:type"

        elif bid.startswith("optype-"):
            op_map = {
                "optype-raid": OperationTypeId.RAID,
                "optype-campaign": OperationTypeId.CAMPAIGN,
                "optype-siege": OperationTypeId.SIEGE,
            }
            chosen = op_map.get(bid)
            if chosen is None:
                return
            self._op_type = chosen
            self.mode = "plan:axis"

        elif bid.startswith("axis-"):
            self._plan_draft["approach_axis"] = bid.split("-")[1]
            self.mode = "plan:prep"

        elif bid.startswith("prep-"):
            self._plan_draft["fire_support_prep"] = bid.split("-")[1]
            self.mode = "plan:posture"

        elif bid.startswith("posture-"):
            self._plan_draft["engagement_posture"] = bid.split("-")[1]
            self.mode = "plan:risk"

        elif bid.startswith("risk-"):
            self._plan_draft["risk_tolerance"] = bid.split("-")[1]
            self.mode = "plan:exploit"

        elif bid.startswith("exploit-"):
            self._plan_draft["exploit_vs_secure"] = bid.split("-")[1]
            self.mode = "plan:end"

        elif bid.startswith("end-"):
            self._plan_draft["end_state"] = bid.split("-")[1]
            if self._target:
                plan = OperationPlan(
                    target=self._target,
                    approach_axis=self._plan_draft["approach_axis"],
                    fire_support_prep=self._plan_draft["fire_support_prep"],
                    engagement_posture=self._plan_draft["engagement_posture"],
                    risk_tolerance=self._plan_draft["risk_tolerance"],
                    exploit_vs_secure=self._plan_draft["exploit_vs_secure"],
                    end_state=self._plan_draft["end_state"],
                    op_type=self._op_type,
                )
                self.state.start_operation(plan)
                self._message = "[bold #c8102e]OPERATION LAUNCHED[/]"
                self.mode = "menu"

        # Production handlers
        elif bid.startswith("prod-cat-"):
            self._prod_category = "supplies" if bid == "prod-cat-supplies" else "army"
            self._prod_job_type = None
            self._prod_quantity = 0
            self.mode = "production:item"

        elif bid.startswith("prod-item-"):
            job_map = {
                "prod-item-ammo": ProductionJobType.AMMO,
                "prod-item-fuel": ProductionJobType.FUEL,
                "prod-item-med": ProductionJobType.MED_SPARES,
                "prod-item-inf": ProductionJobType.INFANTRY,
                "prod-item-walkers": ProductionJobType.WALKERS,
                "prod-item-support": ProductionJobType.SUPPORT,
            }
            job_type = job_map.get(bid)
            if job_type is None:
                return
            self._prod_job_type = job_type
            self._prod_quantity = 0
            self.mode = "production:quantity"

        elif bid.startswith("prod-qty-"):
            delta_map = {
                "prod-qty-minus-50": -50,
                "prod-qty-minus-10": -10,
                "prod-qty-minus-1": -1,
                "prod-qty-plus-1": 1,
                "prod-qty-plus-10": 10,
                "prod-qty-plus-50": 50,
            }
            if bid == "prod-qty-reset":
                self._prod_quantity = 0
                self._request_refresh()
                return
            if bid == "prod-qty-next":
                if self._prod_quantity <= 0:
                    self._message = "[#ff3b3b]SET A QUANTITY BEFORE CONTINUING[/]"
                    self._request_refresh()
                    return
                self.mode = "production:stop"
                return
            delta = delta_map.get(bid)
            if delta is None:
                return
            self._prod_quantity = max(0, self._prod_quantity + delta)
            self._request_refresh()

        elif bid.startswith("prod-stop-"):
            if self._prod_job_type is None:
                return
            if self._prod_quantity <= 0:
                self._message = "[#ff3b3b]SET A QUANTITY BEFORE QUEUING[/]"
                self.mode = "production:quantity"
                return
            stop_map = {
                "prod-stop-core": DepotNode.CORE,
                "prod-stop-mid": DepotNode.MID,
                "prod-stop-front": DepotNode.FRONT,
            }
            stop_at = stop_map.get(bid)
            if stop_at is None:
                return
            self.state.production.queue_job(self._prod_job_type, self._prod_quantity, stop_at)
            self._message = (
                f"[#a7adb5]QUEUED {self._prod_job_type.value.upper()} "
                f"x{self._prod_quantity} -> {stop_at.value.upper()}[/]"
            )
            self._prod_category = None
            self._prod_job_type = None
            self._prod_quantity = 0
            self.mode = "menu"

        elif bid == "prod-back-category":
            self._prod_category = None
            self._prod_job_type = None
            self._prod_quantity = 0
            self.mode = "production"

        elif bid == "prod-back-item":
            self._prod_job_type = None
            self._prod_quantity = 0
            self.mode = "production:item"

        elif bid == "prod-back-qty":
            self.mode = "production:quantity"

        # Logistics handlers
        elif bid.startswith("route-"):
            route_map = {
                "route-core-mid": (DepotNode.CORE, DepotNode.MID),
                "route-mid-front": (DepotNode.MID, DepotNode.FRONT),
            }
            route = route_map.get(bid)
            if route:
                self._pending_route = route
                self.mode = "logistics:package"

        elif bid.startswith("ship-"):
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
            package = package_map.get(bid)
            if package and self._pending_route:
                supplies, units = package
                origin, destination = self._pending_route
                try:
                    self.state.logistics_service.create_shipment(self.state.logistics, origin, destination, supplies, units, self.state.rng)
                except ValueError as exc:
                    self._message = f"[#ff3b3b]{exc}[/]"
                    self.mode = "logistics"
                else:
                    self._message = f"[#a7adb5]SHIPMENT DISPATCHED: {origin.value} -> {destination.value}[/]"
                    self._pending_route = None
                    self.mode = "menu"

        elif bid == "btn-logistics-back":
            self._pending_route = None
            self.mode = "logistics"
