from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static

from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.state import GameState
from clone_wars.engine.types import LocationId, ObjectiveStatus, Supplies, UnitStock


def _pct(value: float) -> int:
    return int(max(0.0, min(1.0, value)) * 100)


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def _fmt_troops(troopers: int) -> str:
    return _fmt_int(troopers)


def _estimate_count(actual: int, confidence: float) -> str:
    confidence = max(0.0, min(1.0, confidence))
    variance = int(round(actual * (1.0 - confidence) * 0.5))
    low = max(0, actual - variance)
    high = actual + variance
    if confidence > 0.9 or variance <= 0:
        return _fmt_int(actual)
    return f"{_fmt_int(low)}-{_fmt_int(high)}"


def _sum_supplies(
    stocks: dict[LocationId, Supplies],
    nodes: Tuple[LocationId, ...] | None = None,
) -> Supplies:
    if nodes is None:
        nodes = tuple(stocks.keys())
    ammo = sum(stocks[node].ammo for node in nodes if node in stocks)
    fuel = sum(stocks[node].fuel for node in nodes if node in stocks)
    med = sum(stocks[node].med_spares for node in nodes if node in stocks)
    return Supplies(ammo=ammo, fuel=fuel, med_spares=med)


def _sum_units(
    units: dict[LocationId, UnitStock],
    nodes: Tuple[LocationId, ...] | None = None,
) -> UnitStock:
    if nodes is None:
        nodes = tuple(units.keys())
    infantry = sum(units[node].infantry for node in nodes if node in units)
    walkers = sum(units[node].walkers for node in nodes if node in units)
    support = sum(units[node].support for node in nodes if node in units)
    return UnitStock(infantry=infantry, walkers=walkers, support=support)


def _format_supplies_summary(supplies: Supplies) -> str:
    return (
        f"AMMO {_fmt_int(supplies.ammo)}, "
        f"FUEL {_fmt_int(supplies.fuel)}, "
        f"MED {_fmt_int(supplies.med_spares)}"
    )


def _format_units_summary(units: UnitStock) -> str:
    return (
        f"INF {_fmt_troops(units.infantry)}, "
        f"WLK {_fmt_int(units.walkers)}, "
        f"SUP {_fmt_int(units.support)}"
    )


def _status_label(status: ObjectiveStatus) -> tuple[str, str]:
    """Return (label, rich_color_name)."""
    if status == ObjectiveStatus.ENEMY:
        return ("ENEMY HELD", "#ff3b3b")
    elif status == ObjectiveStatus.CONTESTED:
        return ("CONTESTED", "#f0b429")
    elif status == ObjectiveStatus.SECURED:
        return ("FRIENDLY", "#e5e7eb")
    return ("UNKNOWN", "#a7adb5")


def _risk_label(risk: float) -> str:
    if risk <= 0.0:
        return "SECURE"
    if risk <= 0.015:
        return "LOW"
    if risk <= 0.04:
        return "ELEVATED"
    return "HIGH"


def _bar(value: int, max_value: int, width: int = 18) -> str:
    if max_value <= 0:
        max_value = 1
    value = max(0, value)
    filled = int(min(1.0, value / max_value) * width)
    return "[" + ("█" * filled) + (" " * (width - filled)) + "]"


class AnimatedCollapsible(Widget):
    """Collapsible container with a small expand/collapse animation."""

    class Contents(Container):
        pass

    collapsed = reactive(False, init=False)
    title = reactive("Panel")

    def __init__(
        self,
        *children: Widget,
        title: str,
        collapsed: bool = False,
        collapsed_symbol: str = "▶",
        expanded_symbol: str = "▼",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._collapsed_symbol = collapsed_symbol
        self._expanded_symbol = expanded_symbol
        self.title = title
        self._contents_list: list[Widget] = list(children)
        self._toggle = Button("", classes="animated-collapsible__title")
        self._contents = AnimatedCollapsible.Contents(classes="animated-collapsible__contents")
        self._expanded_height: int | None = None
        self.collapsed = collapsed

    def compose(self) -> ComposeResult:
        yield self._toggle
        with self._contents:
            yield from self._contents_list

    def compose_add_child(self, widget: Widget) -> None:
        self._contents_list.append(widget)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button is self._toggle:
            self.collapsed = not self.collapsed

    def on_mount(self) -> None:
        self._update_title()
        self.set_class(self.collapsed, "-collapsed")
        self.styles.height = 3 if self.collapsed else "auto"
        self.call_after_refresh(self._capture_expanded_height)
        self._apply_collapsed_styles(animated=False)

    def watch_title(self, title: str) -> None:
        self._update_title()

    def watch_collapsed(self, collapsed: bool) -> None:
        self._update_title()
        self.set_class(collapsed, "-collapsed")
        self.styles.height = 3 if collapsed else "auto"
        self._apply_collapsed_styles(animated=True)

    def _update_title(self) -> None:
        symbol = self._collapsed_symbol if self.collapsed else self._expanded_symbol
        self._toggle.label = f"{symbol} {self.title}"

    def _capture_expanded_height(self) -> None:
        if self.collapsed:
            return
        height = self._contents.size.height
        if height > 0:
            self._expanded_height = height

    def _apply_collapsed_styles(self, *, animated: bool) -> None:
        contents = self._contents
        duration = 0.12 if animated else 0.0

        if self.collapsed:
            if contents.styles.display != "none":
                self._expanded_height = max(contents.size.height, 1)
            contents.styles.display = "block"
            contents.styles.overflow = "hidden"
            contents.styles.opacity = 1.0
            contents.styles.height = self._expanded_height or contents.size.height or 1

            def finish() -> None:
                contents.styles.display = "none"
                contents.styles.height = "auto"
                contents.styles.opacity = 1.0

            if duration:
                contents.animate("styles.opacity", 0.0, duration=duration, easing="out_cubic")
                contents.animate("styles.height", 0, duration=duration, easing="out_cubic", on_complete=finish)
            else:
                finish()
        else:
            target = max(self._expanded_height or 1, 1)
            contents.styles.display = "block"
            contents.styles.overflow = "hidden"
            contents.styles.opacity = 0.0 if duration else 1.0
            contents.styles.height = 0 if duration else "auto"

            def finish() -> None:
                contents.styles.height = "auto"
                contents.styles.opacity = 1.0
                contents.styles.overflow = "visible"
                self.call_after_refresh(self._capture_expanded_height)

            if duration:
                contents.animate("styles.opacity", 1.0, duration=duration, easing="in_out_cubic")
                contents.animate("styles.height", target, duration=duration, easing="in_out_cubic", on_complete=finish)
            else:
                finish()


class HeaderBar(Static):
    """Single-line status header. Uses rich markup for styling."""

    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(markup=True, **kwargs)
        self.state = state

    def render(self) -> str:
        depot_nodes = tuple(self.state.logistics.depot_stocks.keys())
        front_nodes = (LocationId.CONTESTED_FRONT,)
        rest_nodes = tuple(node for node in depot_nodes if node != LocationId.CONTESTED_FRONT)

        front_supplies = _sum_supplies(self.state.logistics.depot_stocks, front_nodes)
        rest_supplies = _sum_supplies(self.state.logistics.depot_stocks, rest_nodes)
        front_units = _sum_units(self.state.logistics.depot_units, front_nodes)
        rest_units = _sum_units(self.state.logistics.depot_units, rest_nodes)

        front_supplies_text = _format_supplies_summary(front_supplies)
        rest_supplies_text = _format_supplies_summary(rest_supplies)
        front_units_text = _format_units_summary(front_units)
        rest_units_text = _format_units_summary(rest_units)

        max_factory_capacity = max(1, self.state.production.max_factories) * self.state.production.slots_per_factory
        max_barracks_capacity = max(1, self.state.barracks.max_barracks) * self.state.barracks.slots_per_barracks
        total_capacity = self.state.production.capacity + self.state.barracks.capacity
        max_total_capacity = max_factory_capacity + max_barracks_capacity
        ic_pct = round(100 * (total_capacity / max_total_capacity)) if max_total_capacity > 0 else 0
        return (
            f"[bold]TURN:[/] {_fmt_int(self.state.day):>3}  |  "
            f"[bold]INDUSTRIAL CAPACITY:[/] {ic_pct}%  |  "
            f"[bold]FRONT SUPPLIES:[/] {front_supplies_text}  |  "
            f"[bold]REST-OF-GLOBE SUPPLIES:[/] {rest_supplies_text}  |  "
            f"[bold]FRONT UNITS:[/] {front_units_text}  |  "
            f"[bold]REST-OF-GLOBE UNITS:[/] {rest_units_text}"
        )


class SituationMap(Widget):
    """Map panel with schematic system layout + objective nodes."""

    can_focus = True

    TARGET_ORDER: tuple[OperationTarget, ...] = (
        OperationTarget.FOUNDRY,
        OperationTarget.COMMS,
        OperationTarget.POWER,
    )

    BINDINGS = [
        ("left", "prev_target", "Prev"),
        ("right", "next_target", "Next"),
        ("enter", "open_selected", "Briefing"),
    ]

    SCHEMATIC_ART = r"""
+------------------------------------+
| . . . . . . . . . . . . . . . . . |
| . . . . . . . . . . . . . . . . . |
| . . . . . . . . . . . . . . . . . |
| . . . . . . . . . . . . . . . . . |
| . . . . . . . . . . . . . . . . . |
| . . . . . . . . . . . . . . . . . |
| . . . . . . . . . . . . . . . . . |
| . . . . . . . . . . . . . . . . . |
+------------------------------------+
"""

    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = state
        self.selected_target: OperationTarget = OperationTarget.FOUNDRY

    def compose(self) -> ComposeResult:
        yield Static("[bold]SITUATION MAP - KEY PLANET: GEONOSIS PRIME[/]", id="system-title", markup=True)

        with Container(id="system-layer"):
            yield Static(self.SCHEMATIC_ART, id="system-art")
            yield Static("----------------------", id="link-top", classes="system-link")
            yield Static("|\n|\n|\n|", id="link-down", classes="system-link")
            yield _SystemNode("D: FOUNDRY", id="map-foundry", classes="system-node")
            yield _SystemNode("C: COMMS", id="map-comms", classes="system-node")
            yield _SystemNode("P: POWER", id="map-power", classes="system-node")

        yield Static(id="system-hint", markup=True)
        yield Static(id="system-sector", markup=True)
        yield Static(id="system-stats", markup=True)

    def on_mount(self) -> None:
        self.refresh_status()

    def action_prev_target(self) -> None:
        if self.state.operation is not None or self.state.raid_session is not None:
            return
        self._cycle_target(-1)

    def action_next_target(self) -> None:
        if self.state.operation is not None or self.state.raid_session is not None:
            return
        self._cycle_target(1)

    def action_open_selected(self) -> None:
        if self.state.operation is not None or self.state.raid_session is not None:
            return
        target = self.selected_target
        if target is None:
            return
        from clone_wars.ui.console import CommandConsole

        try:
            console = self.screen.query_one(CommandConsole)
        except Exception:
            return
        console.open_sector(target)

    def _cycle_target(self, delta: int) -> None:
        order = self.TARGET_ORDER
        try:
            i = order.index(self.selected_target)
        except ValueError:
            i = 0
        self.selected_target = order[(i + delta) % len(order)]
        self.refresh_status()

    def refresh_status(self) -> None:
        obj = self.state.contested_planet.objectives
        f_label, f_color = _status_label(obj.foundry)
        c_label, c_color = _status_label(obj.comms)
        p_label, p_color = _status_label(obj.power)

        hint = "[#a7adb5]Left/Right select | Enter sector briefing | Click node[/]"

        control = _pct(self.state.contested_planet.control)
        fort = self.state.contested_planet.enemy.fortification
        reinf = self.state.contested_planet.enemy.reinforcement_rate
        stats = (
            f"[bold]CONTROL[/] {control}%  "
            f"[bold]FORT[/] {fort:.2f}  "
            f"[bold]REINF[/] {reinf:.2f}"
        )

        self.query_one("#system-hint", Static).update(hint)
        self.query_one("#system-stats", Static).update(stats)

        op = self.state.operation
        active_target: OperationTarget | None = None
        if op is not None:
            active_target = getattr(getattr(op, "intent", None), "target", None)
        if active_target is None and self.state.raid_target is not None:
            active_target = self.state.raid_target
        if active_target is not None:
            self.selected_target = active_target

        self._apply_marker_state(
            "map-foundry",
            obj.foundry,
            active=active_target == OperationTarget.FOUNDRY,
            selected=self.selected_target == OperationTarget.FOUNDRY,
        )
        self._apply_marker_state(
            "map-comms",
            obj.comms,
            active=active_target == OperationTarget.COMMS,
            selected=self.selected_target == OperationTarget.COMMS,
        )
        self._apply_marker_state(
            "map-power",
            obj.power,
            active=active_target == OperationTarget.POWER,
            selected=self.selected_target == OperationTarget.POWER,
        )

        self._refresh_sector_card()

    def _apply_marker_state(
        self, marker_id: str, status: ObjectiveStatus, active: bool, selected: bool
    ) -> None:
        button = self.query_one(f"#{marker_id}", Button)
        button.set_class(status == ObjectiveStatus.ENEMY, "system-node--enemy")
        button.set_class(status == ObjectiveStatus.CONTESTED, "system-node--contested")
        button.set_class(status == ObjectiveStatus.SECURED, "system-node--secured")
        button.set_class(active, "system-node--active")
        button.set_class(selected, "system-node--selected")

    def _refresh_sector_card(self) -> None:
        t = self.selected_target
        obj_id = {
            OperationTarget.FOUNDRY: "foundry",
            OperationTarget.COMMS: "comms",
            OperationTarget.POWER: "power",
        }.get(t)
        obj_def = self.state.rules.objectives.get(obj_id) if obj_id else None
        obj_type = obj_def.type.upper() if obj_def else "UNKNOWN"
        difficulty = obj_def.base_difficulty if obj_def else 1.0

        desc = (obj_def.description if obj_def else "").strip()
        if desc:
            first_line = desc.splitlines()[0].strip()
        else:
            first_line = "No details available."

        self.query_one("#system-sector", Static).update(
            f"[bold]SELECTED[/] {t.value.upper()}  "
            f"[#a7adb5]TYPE[/] {obj_type}  "
            f"[#a7adb5]DIFF[/] x{difficulty:.2f}\n"
            f"[#a7adb5]{first_line}[/]"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if not bid or not bid.startswith("map-"):
            return
        if self.state.operation is not None or self.state.raid_session is not None:
            return

        from clone_wars.ui.console import CommandConsole

        target_map = {
            "map-foundry": OperationTarget.FOUNDRY,
            "map-comms": OperationTarget.COMMS,
            "map-power": OperationTarget.POWER,
        }
        target = target_map.get(bid)
        if target is None:
            return
        self.selected_target = target
        try:
            console = self.screen.query_one(CommandConsole)
        except Exception:
            return
        console.open_sector(target)
        self.refresh_status()


class _SystemNode(Button):
    can_focus = False


class EnemyIntel(Static):
    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(markup=True, **kwargs)
        self.state = state

    def render(self) -> str:
        enemy = self.state.contested_planet.enemy
        conf = enemy.intel_confidence
        fort_label = "HIGH" if enemy.fortification >= 1.0 else "LOW"
        reinf_label = "MODERATE" if enemy.reinforcement_rate >= 0.08 else "LOW"
        return (
            f"[bold]ENEMY FORCE:[/] "
            f"INF {_estimate_count(enemy.infantry, conf)}, "
            f"WLK {_estimate_count(enemy.walkers, conf)}, "
            f"SUP {_estimate_count(enemy.support, conf)} "
            f"({int(conf * 100)}% Conf.)  |  "
            f"[bold]FORTIFICATION:[/] {fort_label}\n"
            f"[bold]REINFORCEMENT:[/] {reinf_label}  |  "
            f"[bold]COHESION:[/] {_pct(enemy.cohesion)}%"
        )


class TaskForcePanel(Static):
    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(markup=True, **kwargs)
        self.state = state

    def render(self) -> str:
        tf = self.state.task_force
        readiness = _pct(tf.readiness)
        cohesion = _pct(tf.cohesion)
        coh_label = "HIGH" if cohesion >= 80 else ("MED" if cohesion >= 50 else "LOW")

        s = tf.supplies
        # Bars are relative to the task force carried capacity proxy (kept simple).
        ammo_bar = _bar(s.ammo, 300)
        fuel_bar = _bar(s.fuel, 200)
        med_bar = _bar(s.med_spares, 150)

        return (
            f"[bold]UNITS:[/] INFANTRY ({_fmt_troops(tf.composition.infantry)}),\n"
            f"       WALKERS ({tf.composition.walkers}), SUPPORT ({tf.composition.support})\n\n"
            f"[bold]READINESS:[/] {readiness}%\n"
            f"[bold]COHESION:[/] {coh_label}\n\n"
            "[bold]SUPPLIES CARRIED:[/]\n"
            f"  A: {_fmt_int(s.ammo):>4} {ammo_bar}\n"
            f"  F: {_fmt_int(s.fuel):>4} {fuel_bar}\n"
            f"  M: {_fmt_int(s.med_spares):>4} {med_bar}\n"
        )


class ProductionPanel(Static):
    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(markup=True, **kwargs)
        self.state = state

    def render(self) -> str:
        prod = self.state.production
        barracks = self.state.barracks

        factory_lines = []
        if prod.jobs:
            for job_type, quantity, eta, stop_at in prod.get_eta_summary():
                label = f"{job_type.upper():<9} x{_fmt_int(quantity)}"
                factory_lines.append(f"  - {label}  ETA {eta}d  -> {stop_at}")
        else:
            factory_lines.append("  - NO ACTIVE QUEUES")

        barracks_lines = []
        if barracks.jobs:
            for job_type, quantity, eta, stop_at in barracks.get_eta_summary():
                label = f"{job_type.upper():<9} x{_fmt_int(quantity)}"
                barracks_lines.append(f"  - {label}  ETA {eta}d  -> {stop_at}")
        else:
            barracks_lines.append("  - NO ACTIVE QUEUES")

        return (
            f"[bold]FACTORY CAPACITY:[/] {prod.capacity} slots/day\n"
            f"[bold]FACTORIES:[/] {prod.factories}/{prod.max_factories} "
            f"({prod.slots_per_factory} slot each)\n"
            "[bold]FACTORY QUEUES:[/]\n"
            + "\n".join(factory_lines)
            + "\n\n"
            f"[bold]BARRACKS CAPACITY:[/] {barracks.capacity} slots/day\n"
            f"[bold]BARRACKS:[/] {barracks.barracks}/{barracks.max_barracks} "
            f"({barracks.slots_per_barracks} slot each)\n"
            "[bold]BARRACKS QUEUES:[/]\n"
            + "\n".join(barracks_lines)
        )


class LogisticsPanel(Widget):
    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = state
        self.selected_depot = LocationId.NEW_SYSTEM_CORE

    def compose(self) -> ComposeResult:
        with Vertical(id="logistics-network"):
            with Horizontal(classes="depot-row"):
                yield Button("CORE", id="depot-core", classes="depot-node")
                yield Static("", id="depot-core-counts", classes="depot-counts")
            yield Static("  ↓", classes="route-arrow-down", markup=True)
            with Horizontal(classes="depot-row"):
                yield Button("MID", id="depot-mid", classes="depot-node")
                yield Static("", id="depot-mid-counts", classes="depot-counts")
            yield Static("  ↓", classes="route-arrow-down", markup=True)
            with Horizontal(classes="depot-row"):
                yield Button("FRONT", id="depot-front", classes="depot-node")
                yield Static("", id="depot-front-counts", classes="depot-counts")

        yield Static("", id="logistics-detail", markup=True)
        yield Static("", id="logistics-shipments", markup=True)

    def on_mount(self) -> None:
        self.refresh_panel()

    def refresh_panel(self) -> None:
        self._update_node_counts()
        self._update_selection()
        self._update_detail()
        self._update_shipments()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if not bid:
            return
        depot_map = {
            "depot-core": LocationId.NEW_SYSTEM_CORE,
            "depot-mid": LocationId.CONTESTED_MID_DEPOT,
            "depot-front": LocationId.CONTESTED_FRONT,
        }
        depot = depot_map.get(bid)
        if depot is None:
            return
        self.selected_depot = depot
        self.refresh_panel()

    def _update_node_counts(self) -> None:
        stocks = self.state.logistics.depot_stocks
        count_map = {
            LocationId.NEW_SYSTEM_CORE: "depot-core-counts",
            LocationId.CONTESTED_MID_DEPOT: "depot-mid-counts",
            LocationId.CONTESTED_FRONT: "depot-front-counts",
        }
        for depot, node_id in count_map.items():
            stock = self._stock_for_display(depot)
            text = f"A{_fmt_int(stock.ammo)} F{_fmt_int(stock.fuel)} M{_fmt_int(stock.med_spares)}"
            self.query_one(f"#{node_id}", Static).update(text)

    def _update_selection(self) -> None:
        btn_map = {
            LocationId.NEW_SYSTEM_CORE: "depot-core",
            LocationId.CONTESTED_MID_DEPOT: "depot-mid",
            LocationId.CONTESTED_FRONT: "depot-front",
        }
        for depot, node_id in btn_map.items():
            button = self.query_one(f"#{node_id}", Button)
            button.set_class(depot == self.selected_depot, "depot-node--selected")

    def _update_detail(self) -> None:
        depot = self.selected_depot
        stock = self._stock_for_display(depot)
        units = self.state.logistics.depot_units[depot]
        storage_risk = self.state.rules.globals.storage_risk_per_day
        storage_loss = self.state.rules.globals.storage_loss_pct_range
        risk = storage_risk.get(depot, 0.0)
        loss_min, loss_max = storage_loss.get(depot, (0.0, 0.0))
        risk_label = _risk_label(risk)
        detail = (
            f"[bold]SELECTED:[/] {depot.value}\n"
            f"[bold]SAFETY:[/] {risk_label}  "
            f"[#a7adb5]Risk {int(risk * 100)}%/day, Loss {int(loss_min * 100)}–{int(loss_max * 100)}%[/]\n"
            f"[bold]STOCK:[/] "
            f"A {_fmt_int(stock.ammo)}  F {_fmt_int(stock.fuel)}  M {_fmt_int(stock.med_spares)}\n"
            f"[bold]UNITS:[/] "
            f"I {_fmt_troops(units.infantry)}  W {_fmt_int(units.walkers)}  S {_fmt_int(units.support)}"
        )
        self.query_one("#logistics-detail", Static).update(detail)

    def _stock_for_display(self, depot: LocationId) -> Supplies:
        if depot == LocationId.CONTESTED_FRONT:
            return self.state.task_force.supplies
        return self.state.logistics.depot_stocks[depot]

    def _update_shipments(self) -> None:
        if self.state.logistics.shipments:
            shipment_lines = ["[bold]IN TRANSIT:[/]"]
            for shipment in self.state.logistics.shipments:
                status = (
                    "[#ff5f5f]⚠ INTERDICTED[/]"
                    if shipment.interdicted
                    else "[#a7adb5]EN ROUTE[/]"
                )
                path = "→".join(node.value for node in shipment.path)  # Simplification for MVP
                leg = f"{shipment.origin.value}->{shipment.destination.value}"
                unit_seg = ""
                if shipment.units.infantry or shipment.units.walkers or shipment.units.support:
                    unit_seg = (
                        f" | I{shipment.units.infantry} W{shipment.units.walkers} "
                        f"S{shipment.units.support}"
                    )
                shipment_lines.append(
                    f"  - #{shipment.shipment_id} {path} ({leg}) | "
                    f"A{shipment.supplies.ammo} F{shipment.supplies.fuel} M{shipment.supplies.med_spares}"
                    f"{unit_seg} | ETA {shipment.days_remaining}d | {status}"
                )
        else:
            shipment_lines = ["[bold]IN TRANSIT:[/]  NONE"]

        # Add constraints summary
        port_cap = self.state.logistics.daily_port_capacity
        port_used = self.state.logistics.convoys_launched_today
        hull_total = self.state.logistics.total_hull_pool
        hull_used = self.state.logistics.used_hull_capacity
        hull_avail = max(0, hull_total - hull_used)
        
        constraints = (
            f"[bold]PORT CAP:[/] {port_used}/{port_cap} daily launches  |  "
            f"[bold]HULL POOL:[/] {hull_avail} available / {hull_total} total"
        )
        
        self.query_one("#logistics-shipments", Static).update(
            constraints + "\n\n" + "\n".join(shipment_lines)
        )


@dataclass()
class FlashMessage:
    text: str
    kind: str = "info"  # info|ok|warn|err


class FlashLine(Static):
    """A thin status line for short confirmations/errors (kept separate from main console)."""

    def __init__(self) -> None:
        super().__init__(markup=True)
        self._msg: FlashMessage | None = None

    def set(self, msg: FlashMessage | None) -> None:
        self._msg = msg
        self.refresh()

    def render(self) -> str:
        if self._msg is None:
            return ""
        color = {
            "info": "#a7adb5",
            "ok": "#e5e7eb",
            "warn": "#f0b429",
            "err": "#ff3b3b",
        }.get(self._msg.kind, "#a7adb5")
        return f"[{color}]{self._msg.text}[/{color}]"
