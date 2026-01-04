"""Tests for command console flow and integration actions."""

from dataclasses import dataclass
from pathlib import Path

from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.production import ProductionJobType
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


def _load_state():
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    return load_game_state(data_dir / "scenario.json")


def test_console_queue_production_job() -> None:
    state = _load_state()
    console = CommandConsole(state)

    console.on_button_pressed(_event("prod-ammo-25"))

    assert len(state.production.jobs) == 1
    job = state.production.jobs[0]
    assert job.job_type == ProductionJobType.AMMO
    assert job.quantity == 25
    assert console.mode == "menu"


def test_console_queue_unit_production_job() -> None:
    state = _load_state()
    console = CommandConsole(state)

    console.on_button_pressed(_event("prod-inf-4"))

    assert len(state.production.jobs) == 1
    job = state.production.jobs[0]
    assert job.job_type == ProductionJobType.INFANTRY
    assert job.quantity == 4


def test_console_create_shipment() -> None:
    state = _load_state()
    console = CommandConsole(state)

    console.on_button_pressed(_event("route-core-mid"))
    assert console.mode == "logistics:package"

    console.on_button_pressed(_event("ship-mixed-1"))

    assert len(state.logistics.shipments) == 1
    shipment = state.logistics.shipments[0]
    assert shipment.origin == DepotNode.CORE
    assert shipment.destination == DepotNode.MID_DEPOT
    assert console.mode == "menu"


def test_console_create_unit_shipment() -> None:
    state = _load_state()
    state.logistics.depot_units[DepotNode.CORE] = UnitStock(infantry=6, walkers=2, support=3)
    console = CommandConsole(state)

    console.on_button_pressed(_event("route-core-mid"))
    console.on_button_pressed(_event("ship-units-1"))

    assert len(state.logistics.shipments) == 1
    shipment = state.logistics.shipments[0]
    assert shipment.units.infantry == 4
    assert shipment.units.walkers == 1
    assert shipment.units.support == 2


def test_console_transfer_to_task_force() -> None:
    state = _load_state()
    state.logistics.depot_stocks[DepotNode.KEY_PLANET] = Supplies(ammo=50, fuel=50, med_spares=50)
    console = CommandConsole(state)
    before = state.task_force.supplies

    console.on_button_pressed(_event("transfer-mixed-1"))

    after = state.task_force.supplies
    assert after.ammo == before.ammo + 20
    assert after.fuel == before.fuel + 15
    assert after.med_spares == before.med_spares + 5
    assert console.mode == "menu"


def test_console_transfer_units_to_task_force() -> None:
    state = _load_state()
    state.logistics.depot_units[DepotNode.KEY_PLANET] = UnitStock(infantry=5, walkers=2, support=3)
    console = CommandConsole(state)
    before = state.task_force.composition

    console.on_button_pressed(_event("transfer-units-1"))

    assert before.infantry + 4 == state.task_force.composition.infantry
    assert before.walkers + 1 == state.task_force.composition.walkers
    assert before.support + 2 == state.task_force.composition.support
    assert console.mode == "menu"


def test_console_transfer_insufficient_stock() -> None:
    state = _load_state()
    state.logistics.depot_stocks[DepotNode.KEY_PLANET] = Supplies(ammo=0, fuel=0, med_spares=0)
    console = CommandConsole(state)

    console.on_button_pressed(_event("transfer-ammo-1"))

    assert console.mode == "logistics"
    assert console._message is not None


def test_console_shipment_insufficient_stock() -> None:
    state = _load_state()
    state.logistics.depot_stocks[DepotNode.CORE] = Supplies(ammo=0, fuel=0, med_spares=0)
    console = CommandConsole(state)

    console.on_button_pressed(_event("route-core-mid"))
    console.on_button_pressed(_event("ship-mixed-1"))

    assert len(state.logistics.shipments) == 0
    assert console.mode == "logistics"
    assert console._message is not None
