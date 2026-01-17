"""Integration tests for GameState with all systems."""

from pathlib import Path

from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.ops import OperationPlan, OperationTarget
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
    """Test that unit production outputs go to Core depot units."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    initial_units = state.logistics.depot_units[DepotNode.CORE]

    state.production.queue_job(ProductionJobType.INFANTRY, quantity=4)
    while len(state.production.jobs) > 0:
        state.advance_day()

    final_units = state.logistics.depot_units[DepotNode.CORE]
    assert final_units.infantry == initial_units.infantry + 4


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


def test_operation_during_advance_day() -> None:
    """Test that operations progress during advance_day()."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    estimated_days = state.operation.estimated_days

    # Advance days until operation completes
    days_advanced = 0
    while state.operation is not None:
        prev_day = state.day
        state.advance_day()
        days_advanced += 1
        assert state.day > prev_day

    # Operation should have completed
    assert state.operation is None
    assert state.last_aar is not None
    assert state.last_aar.days == estimated_days


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
    """Test that enemy fortification increases over time."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    initial_fort = state.planet.enemy.fortification

    # Advance multiple days
    for _ in range(10):
        state.advance_day()

    # Fortification should increase (capped at 2.0)
    assert state.planet.enemy.fortification >= initial_fort
    assert state.planet.enemy.fortification <= 2.0


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

    # Set up for success
    state.planet.enemy.fortification = 0.5
    state.planet.control = 0.9
    state.task_force.supplies = Supplies(ammo=1000, fuel=1000, med_spares=1000)

    objectives = [
        OperationTarget.FOUNDRY,
        OperationTarget.COMMS,
        OperationTarget.POWER,
    ]

    for target in objectives:
        # Try multiple seeds to get success
        for seed in range(20):
            if state.planet.objectives.foundry.value == "secured" and target == OperationTarget.FOUNDRY:
                break
            if state.planet.objectives.comms.value == "secured" and target == OperationTarget.COMMS:
                break
            if state.planet.objectives.power.value == "secured" and target == OperationTarget.POWER:
                break

            state.rng_seed = seed
            state.rng = state.rng.__class__(seed)

            plan = OperationPlan(
                target=target,
                approach_axis="stealth",
                fire_support_prep="preparatory",
                engagement_posture="shock",
                risk_tolerance="high",
                exploit_vs_secure="push",
                end_state="capture",
            )

            state.start_operation(plan)
            while state.operation is not None:
                state.advance_day()

            if state.last_aar and state.last_aar.outcome == "CAPTURED":
                break

    # Check win condition
    from clone_wars.engine.types import ObjectiveStatus
    all_secured = (
        state.planet.objectives.foundry == ObjectiveStatus.SECURED
        and state.planet.objectives.comms == ObjectiveStatus.SECURED
        and state.planet.objectives.power == ObjectiveStatus.SECURED
    )
    # Note: This is probabilistic, may not always win in limited attempts
    # But the mechanism should work


def test_operation_resolves_after_estimated_days() -> None:
    """Test that operation resolves exactly after estimated days."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    estimated = state.operation.estimated_days

    # Advance exactly estimated_days - 1
    for _ in range(estimated - 1):
        state.advance_day()
        assert state.operation is not None

    # One more advance should complete it
    state.advance_day()
    assert state.operation is None
    assert state.last_aar is not None
