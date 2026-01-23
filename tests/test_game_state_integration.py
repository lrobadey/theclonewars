"""Integration tests for GameState with all systems."""

from pathlib import Path

import pytest

from clone_wars.engine.barracks import BarracksJobType
from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.scenario import load_game_state
from clone_wars.engine.types import LocationId, ObjectiveStatus, Supplies, UnitStock


def test_gamestate_initialization() -> None:
    """Test GameState initialization with all systems."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Verify all systems initialized
    assert state.day == 1
    assert state.logistics is not None
    assert state.production is not None
    assert state.barracks is not None
    assert state.rules is not None
    assert state.contested_planet is not None
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
    initial_core = state.logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE].ammo
    state.logistics_service.create_shipment(
        state.logistics,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_MID_DEPOT,
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

    initial_core_ammo = state.logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE].ammo

    # Queue production job
    state.production.queue_job(ProductionJobType.AMMO, quantity=20)

    # Advance until job completes
    while len(state.production.jobs) > 0:
        state.advance_day()

    # Core depot should have received the production
    final_core_ammo = state.logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE].ammo
    assert final_core_ammo == initial_core_ammo + 20


def test_barracks_outputs_to_core_depot() -> None:
    """Test that barracks outputs go to Core depot units."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    initial_units = state.logistics.depot_units[LocationId.NEW_SYSTEM_CORE]

    state.barracks.queue_job(BarracksJobType.INFANTRY, quantity=4)
    while len(state.barracks.jobs) > 0:
        state.advance_day()

    final_units = state.logistics.depot_units[LocationId.NEW_SYSTEM_CORE]
    assert final_units.infantry == initial_units.infantry + 4


def test_production_auto_dispatches_to_stop() -> None:
    """Test that production outputs dispatch to a non-core stop.
    
    Since Core->Mid goes through space first (Core->Deep Space->Spaceport->Mid),
    we now use active_orders with ship transport, not ground shipments.
    """
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    state.production.queue_job(
        ProductionJobType.AMMO,
        quantity=6,
        stop_at=LocationId.CONTESTED_MID_DEPOT,
    )

    while len(state.production.jobs) > 0:
        state.advance_day()

    # Core->Mid goes through space first, so we check active_orders not shipments
    assert len(state.logistics.active_orders) >= 1
    order = state.logistics.active_orders[0]
    assert order.final_destination == LocationId.CONTESTED_MID_DEPOT


def test_raid_updates_state_and_sets_report() -> None:
    """Test that raid applies casualties/supply use and creates a report."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Make outcome deterministic and fast.
    state.task_force.composition.infantry = 200
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.contested_planet.enemy.infantry = 25
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    initial_ammo = state.front_supplies.ammo
    initial_enemy_inf = state.contested_planet.enemy.infantry

    report = state.raid(OperationTarget.FOUNDRY)

    assert state.last_aar is report
    assert report.target == OperationTarget.FOUNDRY
    assert report.outcome == "VICTORY"
    assert state.front_supplies.ammo < initial_ammo
    assert state.contested_planet.enemy.infantry <= initial_enemy_inf


def test_multiple_days_full_integration() -> None:
    """Test multiple days of full system integration."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set up production
    state.production.queue_job(ProductionJobType.FUEL, quantity=15)

    # Set up logistics
    state.logistics_service.create_shipment(
        state.logistics,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_MID_DEPOT,
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

    initial_fort = state.contested_planet.enemy.fortification
    initial_infantry = state.contested_planet.enemy.infantry

    # Advance multiple days
    for _ in range(10):
        state.advance_day()

    # Fortification should increase (capped)
    assert state.contested_planet.enemy.fortification >= initial_fort
    assert state.contested_planet.enemy.fortification <= 2.5
    assert state.contested_planet.enemy.infantry >= initial_infantry


def test_front_stock_is_shared_with_task_force() -> None:
    """Test that Front depot stock and task force supplies are identical."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Seed Front depot and drain task force to force resupply.
    state.logistics.depot_stocks[LocationId.CONTESTED_FRONT] = Supplies(ammo=50, fuel=40, med_spares=30)
    state.logistics.depot_units[LocationId.CONTESTED_FRONT] = UnitStock(infantry=4, walkers=1, support=2)
    state.set_front_supplies(Supplies(ammo=0, fuel=0, med_spares=0))

    state.set_front_supplies(Supplies(ammo=50, fuel=40, med_spares=30))

    assert state.task_force.supplies == state.front_supplies
    assert state.front_supplies == Supplies(ammo=50, fuel=40, med_spares=30)


def test_win_condition_all_objectives() -> None:
    """Test win condition: capturing all 3 objectives."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set up for deterministic success.
    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.set_front_supplies(Supplies(ammo=10_000, fuel=10_000, med_spares=10_000))
    state.contested_planet.enemy.infantry = 10
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0
    state.contested_planet.enemy.cohesion = 1.0

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

    assert state.contested_planet.objectives.foundry == ObjectiveStatus.SECURED
    assert state.contested_planet.objectives.comms == ObjectiveStatus.SECURED
    assert state.contested_planet.objectives.power == ObjectiveStatus.SECURED


def test_raid_fails_against_secured_objective() -> None:
    """Ensure raiding a secured objective is blocked."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.set_front_supplies(Supplies(ammo=10_000, fuel=10_000, med_spares=10_000))
    state.contested_planet.enemy.infantry = 10
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0
    state.contested_planet.enemy.cohesion = 1.0

    target = OperationTarget.FOUNDRY
    report1 = state.raid(target)
    assert report1.outcome == "VICTORY"
    report2 = state.raid(target)
    assert report2.outcome == "VICTORY"
    assert state.contested_planet.objectives.foundry == ObjectiveStatus.SECURED

    with pytest.raises(RuntimeError, match="already secured"):
        state.raid(target)
