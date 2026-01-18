"""Integration tests for GameState with all systems."""

from pathlib import Path

import pytest

from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.scenario import load_game_state
from clone_wars.engine.types import ObjectiveStatus, Supplies, UnitStock


def test_gamestate_initialization() -> None:
    """Test GameState initialization with all systems."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Verify all systems initialized
    assert state.day == 1
    assert state.logistics is not None
    assert state.production is not None
    assert state.rules is not None
    assert state.planet is not None
    assert state.task_force is not None
    assert state.operation is None
    assert state.last_aar is None


def test_advance_day_integrates_all_systems() -> None:
    """Test that advance_day() integrates all systems correctly."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set up production job
    state.production.queue_job(ProductionJobType.AMMO, quantity=6)

    # Set up shipment
    initial_core = state.logistics.depot_stocks[DepotNode.CORE].ammo
    state.logistics_service.create_shipment(
        state.logistics,
        DepotNode.CORE,
        DepotNode.MID,
        Supplies(ammo=50, fuel=0, med_spares=0),
        None,
        state.rng,
    )

    initial_day = state.day
    initial_production_jobs = len(state.production.jobs)
    initial_shipments = len(state.logistics.shipments)

    # Advance day
    state.advance_day()

    # Day should increment
    assert state.day == initial_day + 1

    # Production should progress
    assert len(state.production.jobs) <= initial_production_jobs

    # Logistics should progress
    # (shipment may or may not complete in one day)


def test_production_outputs_to_core_depot() -> None:
    """Test that production outputs go to Core depot."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    initial_core_ammo = state.logistics.depot_stocks[DepotNode.CORE].ammo

    # Queue production job
    state.production.queue_job(ProductionJobType.AMMO, quantity=20)

    # Advance until job completes
    while len(state.production.jobs) > 0:
        state.advance_day()

    # Core depot should have received the production
    final_core_ammo = state.logistics.depot_stocks[DepotNode.CORE].ammo
    assert final_core_ammo == initial_core_ammo + 20


def test_unit_production_outputs_to_core_depot() -> None:
    """Test that unit production outputs go to Core depot units.

    Infantry production uses a quantity in "production units" which produces
    quantity * SQUAD_SIZE troopers (e.g., 4 production units = 80 troopers).
    """
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    initial_units = state.logistics.depot_units[DepotNode.CORE]

    state.production.queue_job(ProductionJobType.INFANTRY, quantity=4)
    while len(state.production.jobs) > 0:
        state.advance_day()

    final_units = state.logistics.depot_units[DepotNode.CORE]
    # 4 production units × 20 troopers per unit = 80 troopers
    assert final_units.infantry == initial_units.infantry + 80


def test_production_auto_dispatches_to_stop() -> None:
    """Test that production outputs dispatch to a non-core stop."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    state.production.queue_job(
        ProductionJobType.AMMO,
        quantity=6,
        stop_at=DepotNode.MID,
    )

    while len(state.production.jobs) > 0:
        state.advance_day()

    assert len(state.logistics.shipments) == 1
    shipment = state.logistics.shipments[0]
    assert shipment.final_destination == DepotNode.MID


def test_raid_updates_state_and_sets_report() -> None:
    """Test that raid applies casualties/supply use and creates a report."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Make outcome deterministic and fast.
    state.task_force.composition.infantry = 200
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.planet.enemy.infantry = 25
    state.planet.enemy.walkers = 0
    state.planet.enemy.support = 0
    state.planet.enemy.fortification = 1.0

    initial_ammo = state.task_force.supplies.ammo
    initial_enemy_inf = state.planet.enemy.infantry

    report = state.raid(OperationTarget.FOUNDRY)

    assert state.last_aar is report
    assert report.target == OperationTarget.FOUNDRY
    assert report.outcome == "VICTORY"
    assert state.task_force.supplies.ammo < initial_ammo
    assert state.planet.enemy.infantry <= initial_enemy_inf


def test_multiple_days_full_integration() -> None:
    """Test multiple days of full system integration."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set up production
    state.production.queue_job(ProductionJobType.FUEL, quantity=15)

    # Set up logistics
    state.logistics_service.create_shipment(
        state.logistics,
        DepotNode.CORE,
        DepotNode.MID,
        Supplies(ammo=30, fuel=20, med_spares=10),
        None,
        state.rng,
    )

    # Advance multiple days
    for _ in range(5):
        state.advance_day()

    # Systems should have progressed
    assert state.day == 6
    # Production may have completed
    # Logistics shipments may have delivered


def test_enemy_passive_effects() -> None:
    """Test that enemy fortification and force can regenerate over time."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    initial_fort = state.planet.enemy.fortification
    initial_infantry = state.planet.enemy.infantry

    # Advance multiple days
    for _ in range(10):
        state.advance_day()

    # Fortification should increase (capped)
    assert state.planet.enemy.fortification >= initial_fort
    assert state.planet.enemy.fortification <= 2.5
    assert state.planet.enemy.infantry >= initial_infantry


def test_front_stock_is_available_to_task_force() -> None:
    """Test that Front depot stock is automatically available to the task force."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Seed Front depot and drain task force to force resupply.
    state.logistics.depot_stocks[DepotNode.FRONT] = Supplies(ammo=50, fuel=40, med_spares=30)
    state.logistics.depot_units[DepotNode.FRONT] = UnitStock(infantry=4, walkers=1, support=2)
    state.task_force.supplies = Supplies(ammo=0, fuel=0, med_spares=0)

    initial_task_force_ammo = state.task_force.supplies.ammo
    initial_infantry = state.task_force.composition.infantry
    front_ammo = state.logistics.depot_stocks[DepotNode.FRONT].ammo

    state.resupply_task_force()

    assert state.task_force.supplies.ammo == initial_task_force_ammo + front_ammo
    assert state.logistics.depot_stocks[DepotNode.FRONT].ammo == 0
    assert state.task_force.composition.infantry == initial_infantry + 4
    assert state.logistics.depot_units[DepotNode.FRONT].infantry == 0


def test_win_condition_all_objectives() -> None:
    """Test win condition: capturing all 3 objectives."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set up for deterministic success.
    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.task_force.supplies = Supplies(ammo=10_000, fuel=10_000, med_spares=10_000)
    state.planet.enemy.infantry = 10
    state.planet.enemy.walkers = 0
    state.planet.enemy.support = 0
    state.planet.enemy.fortification = 1.0
    state.planet.enemy.cohesion = 1.0

    objectives = [
        OperationTarget.FOUNDRY,
        OperationTarget.COMMS,
        OperationTarget.POWER,
    ]

    # Each objective requires 2 successful raids (ENEMY -> CONTESTED -> SECURED).
    for target in objectives:
        state.last_aar = None
        report1 = state.raid(target)
        assert report1.outcome == "VICTORY"
        state.last_aar = None
        report2 = state.raid(target)
        assert report2.outcome == "VICTORY"

    assert state.planet.objectives.foundry == ObjectiveStatus.SECURED
    assert state.planet.objectives.comms == ObjectiveStatus.SECURED
    assert state.planet.objectives.power == ObjectiveStatus.SECURED


def test_raid_fails_against_secured_objective() -> None:
    """Ensure raiding a secured objective is blocked."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.task_force.supplies = Supplies(ammo=10_000, fuel=10_000, med_spares=10_000)
    state.planet.enemy.infantry = 10
    state.planet.enemy.walkers = 0
    state.planet.enemy.support = 0
    state.planet.enemy.fortification = 1.0
    state.planet.enemy.cohesion = 1.0

    target = OperationTarget.FOUNDRY
    report1 = state.raid(target)
    assert report1.outcome == "VICTORY"
    report2 = state.raid(target)
    assert report2.outcome == "VICTORY"
    assert state.planet.objectives.foundry == ObjectiveStatus.SECURED

    with pytest.raises(RuntimeError, match="already secured"):
        state.raid(target)
