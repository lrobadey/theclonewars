from __future__ import annotations

from typing import cast

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static

from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.ops import OperationPlan, OperationTarget
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.state import GameState
from clone_wars.engine.types import Supplies, UnitStock


class CommandConsole(Widget):
    """
    The state-machine console that handles game flow.
    It sits at the bottom and changes its content based on 'mode'.
    """

    # Modes: "menu", "plan:target", "plan:axis", "plan:prep", "plan:posture",
    #        "plan:risk", "plan:exploit", "plan:end", "production", "logistics",
    #        "logistics:package", "logistics:transfer", "executing", "aar"
    mode = reactive("menu")

    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = state
        self._plan_draft: dict[str, str] = {}
        self._target: OperationTarget | None = None
        self._pending_route: tuple[DepotNode, DepotNode] | None = None
        self._message: str | None = None
        self._last_content_key: str = ""

    def compose(self) -> ComposeResult:
        yield Vertical(id="console-content")

    def on_mount(self) -> None:
        pass

    def update_view(self) -> None:
        """Safe entry point for external updates. Only triggers mode changes or guarded refreshes."""
        if self.state.last_aar is not None and self.mode != "aar":
            self.mode = "aar"
        elif self.mode == "menu":
            self._refresh_content()

    def start_plan_with_target(self, target: OperationTarget) -> None:
        if self.state.operation is not None:
            self._message = "[red]OPERATION ALREADY ACTIVE[/]"
            self.mode = "menu"
            return
        self._target = target
        self.mode = "plan:axis"

    def watch_mode(self, mode: str) -> None:
        self._last_content_key = ""
        try:
            self._refresh_content()
        except Exception:
            pass

    def _refresh_content(self) -> None:
        """Clear and rebuild the console content based on current mode."""
        op_day = self.state.operation.day_in_operation if self.state.operation else -1
        content_key = f"{self.mode}:{self.state.operation is not None}:{op_day}:{self.state.last_aar is not None}:{self._message}"

        if content_key == self._last_content_key:
            return

        self._last_content_key = content_key
        container = self.query_one("#console-content")
        container.remove_children()

        if self._message:
            container.mount(Static(self._message, markup=True))

        # --- MAIN MENU ---
        if self.mode == "menu":
            if self.state.operation is not None:
                op = self.state.operation
                container.mount(
                    Static(
                        f"[bold red]ALERT: OPERATION ACTIVE - {op.target.value.upper()}[/]\n"
                        f"DAY {op.day_in_operation} OF {op.estimated_days}  |  STATUS: IN PROGRESS",
                        markup=True,
                    ),
                    Static("waiting for daily reports... (press 'n' or click button to advance day)"),
                    Button("[N] NEXT DAY", id="btn-next"),
                )
            elif self.state.last_aar is not None:
                self.mode = "aar"
            else:
                container.mount(
                    Static("[bold green]COMMAND LINK ESTABLISHED. AWAITING ORDERS.[/]", markup=True),
                    Button("[1] PLAN OFFENSIVE", id="btn-plan"),
                    Button("[2] PRODUCTION", id="btn-production"),
                    Button("[3] LOGISTICS", id="btn-logistics"),
                    Button("[4] NEXT DAY", id="btn-next"),
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
                Static("[bold]PRODUCTION QUEUE[/]", markup=True),
                Button("[A] QUEUE AMMO x25", id="prod-ammo-25"),
                Button("[B] QUEUE AMMO x50", id="prod-ammo-50"),
                Button("[C] QUEUE FUEL x25", id="prod-fuel-25"),
                Button("[D] QUEUE FUEL x50", id="prod-fuel-50"),
                Button("[E] QUEUE MED x15", id="prod-med-15"),
                Button("[F] QUEUE MED x30", id="prod-med-30"),
                Button("[G] QUEUE INFANTRY x4", id="prod-inf-4"),
                Button("[H] QUEUE WALKERS x2", id="prod-walk-2"),
                Button("[I] QUEUE SUPPORT x3", id="prod-sup-3"),
                Button("[Q] BACK", id="btn-cancel"),
            )

        # --- LOGISTICS ---
        elif self.mode == "logistics":
            container.mount(
                Static("[bold]LOGISTICS COMMAND[/]", markup=True),
                Static("SELECT ROUTE TO CREATE SHIPMENT:"),
                Button("[A] CORE -> MID DEPOT", id="route-core-mid"),
                Button("[B] MID DEPOT -> FORWARD DEPOT", id="route-mid-forward"),
                Button("[C] FORWARD DEPOT -> KEY PLANET", id="route-forward-key"),
                Static(""),
                Button("[T] TRANSFER SUPPLIES TO TASK FORCE", id="transfer-task-force"),
                Button("[Q] BACK", id="btn-cancel"),
            )

        elif self.mode == "logistics:package":
            if self._pending_route:
                origin, destination = self._pending_route
                container.mount(
                    Static(
                        f"[bold]SHIPMENT PACKAGE[/] {origin.value} -> {destination.value}",
                        markup=True,
                    ),
                    Button("[A] MIXED (A40 F30 M15)", id="ship-mixed-1"),
                    Button("[B] AMMO RUN (A60)", id="ship-ammo-1"),
                    Button("[C] FUEL RUN (F50)", id="ship-fuel-1"),
                    Button("[D] MED/SPARES (M30)", id="ship-med-1"),
                    Button("[E] INFANTRY (I4)", id="ship-inf-1"),
                    Button("[F] WALKERS (W2)", id="ship-walk-1"),
                    Button("[G] SUPPORT (S3)", id="ship-sup-1"),
                    Button("[H] MIXED UNITS (I4 W1 S2)", id="ship-units-1"),
                    Button("[Q] BACK", id="btn-logistics-back"),
                )
            else:
                self.mode = "logistics"

        elif self.mode == "logistics:transfer":
            container.mount(
                Static("[bold]TRANSFER TO TASK FORCE[/]", markup=True),
                Button("[A] MIXED (A20 F15 M5)", id="transfer-mixed-1"),
                Button("[B] AMMO (A30)", id="transfer-ammo-1"),
                Button("[C] FUEL (F20)", id="transfer-fuel-1"),
                Button("[D] MED/SPARES (M10)", id="transfer-med-1"),
                Button("[E] INFANTRY (I4)", id="transfer-inf-1"),
                Button("[F] WALKERS (W2)", id="transfer-walk-1"),
                Button("[G] SUPPORT (S3)", id="transfer-sup-1"),
                Button("[H] MIXED UNITS (I4 W1 S2)", id="transfer-units-1"),
                Button("[Q] BACK", id="btn-logistics-back"),
            )

        # --- AAR REPORT ---
        elif self.mode == "aar":
            aar = self.state.last_aar
            if aar:
                color = "green" if "CAPTURED" in aar.outcome or "RAIDED" in aar.outcome else "red"
                container.mount(
                    Static(f"[bold {color}]MISSION COMPLETE: {aar.outcome}[/]", markup=True),
                    Static(
                        f"TARGET: {aar.target.value} | LOSSES: {aar.losses} | DAYS: {aar.days}\n"
                        f"KEY FACTOR: {aar.top_factors[0].why if aar.top_factors else 'N/A'}"
                    ),
                    Button("[ACKNOWLEDGE]", id="btn-ack"),
                )
            else:
                self.mode = "menu"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if not bid:
            return

        # Main Menu handlers
        if bid == "btn-plan":
            self.mode = "plan:target"
        elif bid == "btn-next":
            self.app.run_action("next_day")
            self._message = "[green]DAY ADVANCED[/]"
        elif bid == "btn-cancel":
            self._pending_route = None
            self.mode = "menu"
        elif bid == "btn-ack":
            self.state.last_aar = None
            self.mode = "menu"
        elif bid == "btn-production":
            self.mode = "production"
        elif bid == "btn-logistics":
            self.mode = "logistics"

        # Planning Handlers
        elif bid.startswith("target-"):
            t_map = {
                "target-foundry": OperationTarget.FOUNDRY,
                "target-comms": OperationTarget.COMMS,
                "target-power": OperationTarget.POWER,
            }
            self._target = t_map.get(bid)
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
                )
                self.state.start_operation(plan)
                self._message = "[green]OPERATION LAUNCHED[/]"
                self.mode = "menu"

        # Production handlers
        elif bid.startswith("prod-"):
            job_map = {
                "prod-ammo-25": (ProductionJobType.AMMO, 25),
                "prod-ammo-50": (ProductionJobType.AMMO, 50),
                "prod-fuel-25": (ProductionJobType.FUEL, 25),
                "prod-fuel-50": (ProductionJobType.FUEL, 50),
                "prod-med-15": (ProductionJobType.MED_SPARES, 15),
                "prod-med-30": (ProductionJobType.MED_SPARES, 30),
                "prod-inf-4": (ProductionJobType.INFANTRY, 4),
                "prod-walk-2": (ProductionJobType.WALKERS, 2),
                "prod-sup-3": (ProductionJobType.SUPPORT, 3),
            }
            job = job_map.get(bid)
            if job:
                job_type, quantity = job
                self.state.production.queue_job(job_type, quantity)
                self._message = f"[green]QUEUED {job_type.value.upper()} x{quantity}[/]"
                self.mode = "menu"

        # Logistics handlers
        elif bid.startswith("route-"):
            route_map = {
                "route-core-mid": (DepotNode.CORE, DepotNode.MID_DEPOT),
                "route-mid-forward": (DepotNode.MID_DEPOT, DepotNode.FORWARD_DEPOT),
                "route-forward-key": (DepotNode.FORWARD_DEPOT, DepotNode.KEY_PLANET),
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
                    self.state.logistics.create_shipment(origin, destination, supplies, units, self.state.rng)
                except ValueError as exc:
                    self._message = f"[red]{exc}[/]"
                    self.mode = "logistics"
                else:
                    self._message = f"[green]SHIPMENT DISPATCHED: {origin.value} -> {destination.value}[/]"
                    self._pending_route = None
                    self.mode = "menu"

        elif bid == "transfer-task-force":
            self.mode = "logistics:transfer"

        elif bid.startswith("transfer-"):
            transfer_map = {
                "transfer-mixed-1": (Supplies(ammo=20, fuel=15, med_spares=5), UnitStock(0, 0, 0)),
                "transfer-ammo-1": (Supplies(ammo=30, fuel=0, med_spares=0), UnitStock(0, 0, 0)),
                "transfer-fuel-1": (Supplies(ammo=0, fuel=20, med_spares=0), UnitStock(0, 0, 0)),
                "transfer-med-1": (Supplies(ammo=0, fuel=0, med_spares=10), UnitStock(0, 0, 0)),
                "transfer-inf-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(4, 0, 0)),
                "transfer-walk-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(0, 2, 0)),
                "transfer-sup-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(0, 0, 3)),
                "transfer-units-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(4, 1, 2)),
            }
            package = transfer_map.get(bid)
            if package:
                supplies, units = package
                stock = self.state.logistics.depot_stocks[DepotNode.KEY_PLANET]
                unit_stock = self.state.logistics.depot_units[DepotNode.KEY_PLANET]
                if (
                    stock.ammo < supplies.ammo
                    or stock.fuel < supplies.fuel
                    or stock.med_spares < supplies.med_spares
                    or unit_stock.infantry < units.infantry
                    or unit_stock.walkers < units.walkers
                    or unit_stock.support < units.support
                ):
                    self._message = "[red]INSUFFICIENT STOCK AT KEY PLANET[/]"
                    self.mode = "logistics"
                else:
                    self.state.logistics.depot_stocks[DepotNode.KEY_PLANET] = Supplies(
                        ammo=stock.ammo - supplies.ammo,
                        fuel=stock.fuel - supplies.fuel,
                        med_spares=stock.med_spares - supplies.med_spares,
                    )
                    self.state.logistics.depot_units[DepotNode.KEY_PLANET] = UnitStock(
                        infantry=unit_stock.infantry - units.infantry,
                        walkers=unit_stock.walkers - units.walkers,
                        support=unit_stock.support - units.support,
                    )
                    tf = self.state.task_force.supplies
                    self.state.task_force.supplies = Supplies(
                        ammo=tf.ammo + supplies.ammo,
                        fuel=tf.fuel + supplies.fuel,
                        med_spares=tf.med_spares + supplies.med_spares,
                    )
                    tf_units = self.state.task_force.composition
                    tf_units.infantry += units.infantry
                    tf_units.walkers += units.walkers
                    tf_units.support += units.support
                    self._message = "[green]SUPPLIES TRANSFERRED TO TASK FORCE[/]"
                    self.mode = "menu"

        elif bid == "btn-logistics-back":
            self._pending_route = None
            self.mode = "logistics"
