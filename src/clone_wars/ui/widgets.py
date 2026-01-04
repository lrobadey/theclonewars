from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widget import Widget
from textual.widgets import Button, Static

from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.state import GameState
from clone_wars.engine.types import ObjectiveStatus, Supplies, UnitStock


def _pct(value: float) -> int:
    return int(max(0.0, min(1.0, value)) * 100)


def _fmt_int(n: int) -> str:
    return f"{n:,}"


def _sum_supplies(stocks: dict[DepotNode, Supplies]) -> Supplies:
    ammo = sum(s.ammo for s in stocks.values())
    fuel = sum(s.fuel for s in stocks.values())
    med = sum(s.med_spares for s in stocks.values())
    return Supplies(ammo=ammo, fuel=fuel, med_spares=med)


def _sum_units(units: dict[DepotNode, UnitStock]) -> UnitStock:
    infantry = sum(u.infantry for u in units.values())
    walkers = sum(u.walkers for u in units.values())
    support = sum(u.support for u in units.values())
    return UnitStock(infantry=infantry, walkers=walkers, support=support)


def _status_label(status: ObjectiveStatus) -> tuple[str, str]:
    """Return (label, rich_color_name)."""
    match status:
        case ObjectiveStatus.ENEMY:
            return ("ENEMY HELD", "red")
        case ObjectiveStatus.CONTESTED:
            return ("CONTESTED", "yellow")
        case ObjectiveStatus.SECURED:
            return ("FRIENDLY", "green")


def _bar(value: int, max_value: int, width: int = 18) -> str:
    if max_value <= 0:
        max_value = 1
    value = max(0, value)
    filled = int(min(1.0, value / max_value) * width)
    return "[" + ("█" * filled) + (" " * (width - filled)) + "]"


class HeaderBar(Static):
    """Single-line status header. Uses rich markup for styling."""

    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(markup=True, **kwargs)
        self.state = state

    def render(self) -> str:
        totals = _sum_supplies(self.state.logistics.depot_stocks)
        unit_totals = _sum_units(self.state.logistics.depot_units)
        ic_pct = min(99, max(10, self.state.production.capacity * 25))
        return (
            f"[bold]TURN:[/] {_fmt_int(self.state.day):>3}  |  "
            f"[bold]INDUSTRIAL CAPACITY:[/] {ic_pct}%  |  "
            f"[bold]GLOBAL SUPPLIES:[/] "
            f"AMMO {_fmt_int(totals.ammo)}, FUEL {_fmt_int(totals.fuel)}, MED {_fmt_int(totals.med_spares)}  |  "
            f"[bold]GLOBAL UNITS:[/] "
            f"INF {_fmt_int(unit_totals.infantry)}, WLK {_fmt_int(unit_totals.walkers)}, SUP {_fmt_int(unit_totals.support)}"
        )


class SituationMap(Widget):
    """Map panel with ASCII globe + clickable objective markers."""

    MAP_ART = r"""
.,:;iiiiiiiiii;:,..
      .;i;;;itiiiiiiiiiiii;;;,.
    .;;i;;;;;;;iii;iiiiiiiiiii;;.
   .;;;;;;;;;;;iiiiiiiiiiiiiiiii;;,
  ,;;;;;;;;;;;;;iiiiiiiiiiiiiiiiii;,
 .,;;;;;;;;;;;;;;iiiiiiiiiiiiiiiiii;.
 ,;;;;;;;:.  .:;;iiiiiiiiiiiiiiiiii;,
 ,;;;;;;.      .;iiiiiiiiiiiiiiiiii;,
 ,;;;;;         ;iiiiiiiiiiiiiiiiii;,
 ,;;;;;         ;iiiiiiiiiiiiiiiiii;,
 ,;;;;;.       .;iiiiiiiiiiiiiiiiii;,
 .,;;;;;:.   .:;iiiiiiiiiiiiiiiiiii;.
  ,;;;;;;;;;;;;;iiiiiiiiiiiiiiiiii;,
   ,;;;;;;;;;;;;iiiiiiiiiiiiiiii;,.
    .,;;;;;;;;;;iiiiiiiiiiiiii;,.
      .,;;;;;;;;iiiiiiiiiii;,.
         ..,::;;;;;;;;;::..
"""

    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = state

    def compose(self) -> ComposeResult:
        yield Static("[bold]SITUATION MAP - KEY PLANET: GEONOSIS PRIME[/]", id="planet-title", markup=True)

        with Container(id="planet-layer"):
            yield Static(self.MAP_ART, id="planet-art")
            yield Button("D", id="map-foundry", classes="planet-node")
            yield Button("C", id="map-comms", classes="planet-node")
            yield Button("P", id="map-power", classes="planet-node")

        yield Static(id="planet-legend", markup=True)
        yield Static(id="planet-stats", markup=True)

    def on_mount(self) -> None:
        self.refresh_status()

    def refresh_status(self) -> None:
        obj = self.state.planet.objectives
        f_label, f_color = _status_label(obj.foundry)
        c_label, c_color = _status_label(obj.comms)
        p_label, p_color = _status_label(obj.power)

        # Use a compact legend like the screenshot.
        foundry = f"[{f_color}][D] Droid Foundry ({f_label})[/{f_color}]"
        comms = f"[{c_color}][C] Comm Array ({c_label})[/{c_color}]"
        power = f"[{p_color}][P] Power Plant ({p_label})[/{p_color}]"

        legend = f"    {foundry}\n\n    {comms}\n    {power}"

        control = _pct(self.state.planet.control)
        fort = self.state.planet.enemy.fortification
        reinf = self.state.planet.enemy.reinforcement_rate
        stats = (
            f"[bold]CONTROL[/] {control}%  "
            f"[bold]FORT[/] {fort:.2f}  "
            f"[bold]REINF[/] {reinf:.2f}"
        )

        self.query_one("#planet-legend", Static).update(legend)
        self.query_one("#planet-stats", Static).update(stats)

        active_target = self.state.operation.plan.target if self.state.operation else None
        self._apply_marker_state("map-foundry", obj.foundry, active_target == OperationTarget.FOUNDRY)
        self._apply_marker_state("map-comms", obj.comms, active_target == OperationTarget.COMMS)
        self._apply_marker_state("map-power", obj.power, active_target == OperationTarget.POWER)

    def _apply_marker_state(self, marker_id: str, status: ObjectiveStatus, active: bool) -> None:
        button = self.query_one(f"#{marker_id}", Button)
        button.set_class(status == ObjectiveStatus.ENEMY, "planet-node--enemy")
        button.set_class(status == ObjectiveStatus.CONTESTED, "planet-node--contested")
        button.set_class(status == ObjectiveStatus.SECURED, "planet-node--secured")
        button.set_class(active, "planet-node--active")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if not bid or not bid.startswith("map-"):
            return
        if self.state.operation is not None:
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
        try:
            console = self.screen.query_one(CommandConsole)
        except Exception:
            return
        console.start_plan_with_target(target)


class EnemyIntel(Static):
    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(markup=True, **kwargs)
        self.state = state

    def render(self) -> str:
        enemy = self.state.planet.enemy
        fort_label = "HIGH" if enemy.fortification >= 1.0 else "LOW"
        reinf_label = "MODERATE" if enemy.reinforcement_rate >= 0.08 else "LOW"
        return (
            f"[bold]ENEMY STRENGTH:[/] {enemy.strength_min:.1f}–{enemy.strength_max:.1f} "
            f"({int(enemy.confidence * 100)}% Conf.)  |  "
            f"[bold]FORTIFICATION:[/] {fort_label}\n"
            f"[bold]REINFORCEMENT:[/] {reinf_label}"
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
            "[bold]TASK FORCE: REPUBLIC HAMMER[/]\n"
            f"[bold]UNITS:[/] INFANTRY ({tf.composition.infantry}),\n"
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
        if prod.jobs:
            job_lines = [
                f"  - {job.job_type.value.upper():<9} x{job.quantity}  ETA {job.days_remaining}d"
                for job in prod.jobs
            ]
        else:
            job_lines = ["  - NO ACTIVE QUEUES"]
        return (
            "[bold]PRODUCTION COMMAND[/]\n"
            f"[bold]CAPACITY:[/] {prod.capacity} slots/day\n"
            "[bold]QUEUES:[/]\n"
            + "\n".join(job_lines)
        )


class LogisticsPanel(Static):
    def __init__(self, state: GameState, **kwargs) -> None:
        super().__init__(markup=True, **kwargs)
        self.state = state

    def render(self) -> str:
        stocks = self.state.logistics.depot_stocks
        units = self.state.logistics.depot_units
        depot_lines = []
        for depot in DepotNode:
            stock = stocks[depot]
            unit_stock = units[depot]
            depot_lines.append(
                f"  - {depot.value:<13} A:{_fmt_int(stock.ammo):>4} "
                f"F:{_fmt_int(stock.fuel):>4} M:{_fmt_int(stock.med_spares):>4}  |  "
                f"I:{_fmt_int(unit_stock.infantry):>3} W:{_fmt_int(unit_stock.walkers):>3} S:{_fmt_int(unit_stock.support):>3}"
            )

        if self.state.logistics.shipments:
            shipment_lines = []
            for shipment in self.state.logistics.shipments:
                status = "INTERDICTED" if shipment.interdicted else "EN ROUTE"
                shipment_lines.append(
                    f"  - {shipment.origin.value} -> {shipment.destination.value} | "
                    f"A:{shipment.supplies.ammo} F:{shipment.supplies.fuel} M:{shipment.supplies.med_spares} "
                    f"I:{shipment.units.infantry} W:{shipment.units.walkers} S:{shipment.units.support} | "
                    f"ETA {shipment.days_remaining}d | {status}"
                )
        else:
            shipment_lines = ["  - NO ACTIVE SHIPMENTS"]

        return (
            "[bold]LOGISTICS NETWORK[/]\n"
            "[bold]DEPOTS:[/]\n"
            + "\n".join(depot_lines)
            + "\n\n[bold]SHIPMENTS:[/]\n"
            + "\n".join(shipment_lines)
        )


@dataclass(slots=True)
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
        color = {"info": "cyan", "ok": "green", "warn": "yellow", "err": "red"}.get(self._msg.kind, "cyan")
        return f"[{color}]{self._msg.text}[/{color}]"
