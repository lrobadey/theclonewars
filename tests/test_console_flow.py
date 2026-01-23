"""Tests for command console flow and integration actions."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from clone_wars.engine.barracks import BarracksJobType
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.types import LocationId
from clone_wars.engine.scenario import load_game_state
from clone_wars.engine.types import Supplies, UnitStock
from clone_wars.ui.console import CommandConsole


@dataclass
class _DummyButton:
    id: str


@dataclass
class _DummyEvent:
    button: _DummyButton


def _event(button_id: str) -> _DummyEvent:
    return _DummyEvent(button=_DummyButton(id=button_id))

def _press(console: CommandConsole, button_id: str) -> None:
    asyncio.run(console.on_button_pressed(_event(button_id)))


def _load_state():
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    return load_game_state(data_dir / "scenario.json")


def test_console_queue_production_job() -> None:
    state = _load_state()
    console = CommandConsole(state)

    _press(console, "btn-production")
    _press(console, "prod-cat-supplies")
    _press(console, "prod-item-ammo")
    _press(console, "prod-qty-plus-10")
    _press(console, "prod-qty-next")
    _press(console, "prod-stop-core")

    assert len(state.production.jobs) == 1
    job = state.production.jobs[0]
    assert job.job_type == ProductionJobType.AMMO
    assert job.quantity == 10
    assert job.stop_at == LocationId.NEW_SYSTEM_CORE
    assert console.mode == "menu"


def test_console_queue_unit_production_job() -> None:
    state = _load_state()
    console = CommandConsole(state)

    _press(console, "btn-barracks")
    _press(console, "barracks-item-inf")
    _press(console, "barracks-qty-plus-10")
    _press(console, "barracks-qty-next")
    _press(console, "barracks-stop-core")

    assert len(state.barracks.jobs) == 1
    job = state.barracks.jobs[0]
    assert job.job_type == BarracksJobType.INFANTRY
    assert job.quantity == 10
    assert job.stop_at == LocationId.NEW_SYSTEM_CORE


def test_console_create_shipment() -> None:
    state = _load_state()
    console = CommandConsole(state)

    _press(console, "route-core-mid")
    assert console.mode == "logistics:package"

    _press(console, "ship-mixed-1")

    # Core->Mid goes through space first (Core->Deep Space), so it creates an order on a ship
    assert len(state.logistics.active_orders) == 1
    order = state.logistics.active_orders[0]
    assert order.origin == LocationId.NEW_SYSTEM_CORE
    assert order.final_destination == LocationId.CONTESTED_MID_DEPOT
    assert order.status == "transit"
    assert console.mode == "menu"


def test_console_create_unit_shipment() -> None:
    state = _load_state()
    # Set up depot with enough troopers for the shipment (80 infantry, 1 walker, 2 support)
    state.logistics.depot_units[LocationId.NEW_SYSTEM_CORE] = UnitStock(infantry=100, walkers=2, support=3)
    console = CommandConsole(state)

    _press(console, "route-core-mid")
    _press(console, "ship-units-1")

    # Core->Mid goes through space first, so it creates an order on a ship
    assert len(state.logistics.active_orders) == 1
    order = state.logistics.active_orders[0]
    # Order carries 80 troopers, 1 walker, 2 support
    assert order.units.infantry == 80
    assert order.units.walkers == 1
    assert order.units.support == 2


def test_console_create_shipment_mid_front() -> None:
    state = _load_state()
    console = CommandConsole(state)
    # Add stock at mid depot for the shipment
    state.logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT] = Supplies(ammo=100, fuel=100, med_spares=50)

    _press(console, "route-mid-front")
    assert console.mode == "logistics:package"

    _press(console, "ship-ammo-1")

    # Mid->Front is a ground leg, so it creates a ground shipment
    assert len(state.logistics.shipments) == 1
    shipment = state.logistics.shipments[0]
    assert shipment.origin == LocationId.CONTESTED_MID_DEPOT
    assert shipment.destination == LocationId.CONTESTED_FRONT
    assert console.mode == "menu"


def test_console_shipment_insufficient_stock() -> None:
    state = _load_state()
    state.logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE] = Supplies(ammo=0, fuel=0, med_spares=0)
    console = CommandConsole(state)

    _press(console, "route-core-mid")
    _press(console, "ship-mixed-1")

    assert len(state.logistics.shipments) == 0
    assert console.mode == "logistics"
    assert console._message is not None
