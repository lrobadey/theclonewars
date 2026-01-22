"""Comprehensive tests for logistics system."""

from random import Random

import pytest

from clone_wars.engine.logistics import LogisticsState
from clone_wars.engine.services.logistics import LogisticsService
from clone_wars.engine.types import EnemyForce, LocationId, Objectives, ObjectiveStatus, PlanetState, Supplies, UnitStock


def _dummy_planet() -> PlanetState:
    return PlanetState(
        objectives=Objectives(
            foundry=ObjectiveStatus.ENEMY,
            comms=ObjectiveStatus.ENEMY,
            power=ObjectiveStatus.ENEMY,
        ),
        enemy=EnemyForce(
            infantry=100,
            walkers=2,
            support=1,
            cohesion=1.0,
            fortification=1.0,
            reinforcement_rate=0.0,
            intel_confidence=0.7,
        ),
        control=0.3,
    )


def test_logistics_initial_state() -> None:
    """Test initial logistics state structure."""
    logistics = LogisticsState.new()

    # Verify all depots exist
    assert LocationId.NEW_SYSTEM_CORE in logistics.depot_stocks
    assert LocationId.CONTESTED_MID_DEPOT in logistics.depot_stocks
    assert LocationId.CONTESTED_FRONT in logistics.depot_stocks

    # Verify initial stocks are non-negative
    for depot, stock in logistics.depot_stocks.items():
        assert stock.ammo >= 0
        assert stock.fuel >= 0
        assert stock.med_spares >= 0

    # Verify routes exist
    assert len(logistics.routes) == 4
    for route in logistics.routes:
        assert route.origin in LocationId
        assert route.destination in LocationId
        assert route.travel_days > 0
        assert 0.0 <= route.interdiction_risk <= 1.0


def test_create_shipment_all_supplies() -> None:
    """Test creating shipment with all supply types."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    initial_core = logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE]

    service.create_shipment(
        logistics,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_MID_DEPOT,
        Supplies(ammo=50, fuel=40, med_spares=20),
        None,
        rng,
    )

    # Verify stock deducted
    new_core = logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE]
    assert new_core.ammo == initial_core.ammo - 50
    assert new_core.fuel == initial_core.fuel - 40
    assert new_core.med_spares == initial_core.med_spares - 20

    # Verify shipment created
    assert len(logistics.shipments) == 1
    shipment = logistics.shipments[0]
    assert shipment.supplies.ammo == 50
    assert shipment.supplies.fuel == 40
    assert shipment.supplies.med_spares == 20


def test_create_shipment_no_route() -> None:
    """Test creating shipment to non-existent route."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)

    with pytest.raises(ValueError, match="No route"):
        service.create_shipment(
            logistics,
            LocationId.CONTESTED_FRONT,
            LocationId.NEW_SYSTEM_CORE,  # Reverse route doesn't exist
            Supplies(ammo=10, fuel=10, med_spares=10),
            None,
            rng,
        )


def test_create_shipment_partial_shortage() -> None:
    """Test creating shipment with partial stock shortage."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE] = Supplies(ammo=100, fuel=5, med_spares=100)

    with pytest.raises(ValueError, match="Insufficient stock"):
        service.create_shipment(
            logistics,
            LocationId.NEW_SYSTEM_CORE,
            LocationId.CONTESTED_MID_DEPOT,
            Supplies(ammo=50, fuel=10, med_spares=50),  # fuel insufficient
            None,
            rng,
        )


def test_multiple_shipments() -> None:
    """Test multiple shipments in transit simultaneously."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)

    # Create multiple shipments
    service.create_shipment(
        logistics,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_MID_DEPOT,
        Supplies(ammo=50, fuel=0, med_spares=0),
        None,
        rng,
    )
    service.create_shipment(
        logistics,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_MID_DEPOT,
        Supplies(ammo=30, fuel=20, med_spares=0),
        None,
        rng,
    )

    assert len(logistics.shipments) == 2
    assert logistics.shipments[0].origin == LocationId.NEW_SYSTEM_CORE
    assert logistics.shipments[1].origin == LocationId.NEW_SYSTEM_CORE


def test_shipment_delivery_chain() -> None:
    """Test shipment traveling through the network path."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    planet = _dummy_planet()
    initial_front = logistics.depot_stocks[LocationId.CONTESTED_FRONT].ammo
    for route in logistics.routes:
        route.interdiction_risk = 0.0

    service.create_shipment(
        logistics,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_FRONT,
        Supplies(ammo=30, fuel=0, med_spares=0),
        None,
        rng,
    )

    shipment = logistics.shipments[0]
    while logistics.shipments:
        service.tick(logistics, planet, rng)

    assert logistics.depot_stocks[LocationId.CONTESTED_FRONT].ammo == initial_front + 30


def test_interdiction_probability() -> None:
    """Test that interdiction occurs with correct probability over many runs."""
    logistics_initial = LogisticsState.new()
    service = LogisticsService()
    planet = _dummy_planet()

    # Use route with high interdiction risk
    mid_to_front_route = next(
        r for r in logistics_initial.routes
        if r.origin == LocationId.CONTESTED_MID_DEPOT and r.destination == LocationId.CONTESTED_FRONT
    )
    assert mid_to_front_route.interdiction_risk > 0.1

    interdicted_count = 0
    total_runs = 100

    for seed in range(total_runs):
        logistics = LogisticsState.new()
        logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT] = Supplies(ammo=100, fuel=50, med_spares=30)
        rng = Random(seed)
        service.create_shipment(
            logistics,
            LocationId.CONTESTED_MID_DEPOT,
            LocationId.CONTESTED_FRONT,
            Supplies(ammo=100, fuel=0, med_spares=0),
            None,
            rng,
        )
        service.tick(logistics, planet, rng)
        if logistics.shipments[0].interdicted:
            interdicted_count += 1

    # With 20% risk over 100 runs, we should see some interdictions
    # (not testing exact probability, just that mechanism works)
    assert interdicted_count > 0  # Should have at least some interdictions


def test_interdiction_supply_loss() -> None:
    """Test that interdiction reduces supplies correctly."""
    service = LogisticsService()
    planet = _dummy_planet()
    # Find a seed that triggers interdiction
    for seed in range(100):
        logistics = LogisticsState.new()
        logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT] = Supplies(ammo=100, fuel=50, med_spares=30)
        rng = Random(seed)
        original_ammo = 100
        service.create_shipment(
            logistics,
            LocationId.CONTESTED_MID_DEPOT,
            LocationId.CONTESTED_FRONT,
            Supplies(ammo=original_ammo, fuel=50, med_spares=30),
            None,
            rng,
        )
        service.tick(logistics, planet, rng)
        if logistics.shipments[0].interdicted:
            shipment = logistics.shipments[0]
            # Should have lost 20-40%
            assert shipment.supplies.ammo < original_ammo
            assert shipment.supplies.ammo >= original_ammo * 0.6  # At least 60% remains
            assert shipment.supplies.ammo <= original_ammo * 0.9  # At most 90% remains
            break


def test_shipment_total_days_tracking() -> None:
    """Test that shipment tracks total days correctly."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    planet = _dummy_planet()

    service.create_shipment(
        logistics,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_MID_DEPOT,
        Supplies(ammo=50, fuel=0, med_spares=0),
        None,
        rng,
    )

    shipment = logistics.shipments[0]
    total_days = shipment.total_days
    assert total_days > 0
    assert shipment.days_remaining == total_days

    # After one tick
    service.tick(logistics, planet, rng)
    assert shipment.days_remaining == total_days - 1


def test_empty_logistics_tick() -> None:
    """Test that tick works with no shipments."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    planet = _dummy_planet()

    # Should not raise error
    service.tick(logistics, planet, rng)
    assert len(logistics.shipments) == 0


def test_shipment_delivery_preserves_other_stocks() -> None:
    """Test that delivery doesn't affect other supply types incorrectly."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    planet = _dummy_planet()
    initial_mid = logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT]

    service.create_shipment(
        logistics,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_MID_DEPOT,
        Supplies(ammo=50, fuel=0, med_spares=0),
        None,
        rng,
    )

    shipment = logistics.shipments[0]
    days = shipment.days_remaining

    for _ in range(days):
        service.tick(logistics, planet, rng)

    final_mid = logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT]
    # Only ammo should increase
    assert final_mid.ammo == initial_mid.ammo + 50
    assert final_mid.fuel == initial_mid.fuel
    assert final_mid.med_spares == initial_mid.med_spares


def test_unit_shipment_delivery() -> None:
    """Test that unit shipments deliver to depot unit stock."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(7)
    planet = _dummy_planet()
    initial_units = logistics.depot_units[LocationId.CONTESTED_MID_DEPOT]
    logistics.depot_units[LocationId.NEW_SYSTEM_CORE] = UnitStock(infantry=10, walkers=5, support=4)

    service.create_shipment(
        logistics,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_MID_DEPOT,
        Supplies(ammo=0, fuel=0, med_spares=0),
        UnitStock(infantry=4, walkers=1, support=2),
        rng=rng,
    )

    shipment = logistics.shipments[0]
    for _ in range(shipment.days_remaining):
        service.tick(logistics, planet, rng)

    final_units = logistics.depot_units[LocationId.CONTESTED_MID_DEPOT]
    assert final_units.infantry == initial_units.infantry + 4
    assert final_units.walkers == initial_units.walkers + 1
    assert final_units.support == initial_units.support + 2
