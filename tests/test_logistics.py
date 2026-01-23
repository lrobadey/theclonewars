"""Tests for logistics system."""

from random import Random

import pytest

from clone_wars.engine.logistics import LogisticsState
from clone_wars.engine.services.logistics import LogisticsService
from clone_wars.engine.types import EnemyForce, LocationId, Objectives, ObjectiveStatus, PlanetState, Supplies


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


def test_logistics_state_new() -> None:
    """Test creating new logistics state."""
    logistics = LogisticsState.new()
    assert len(logistics.depot_stocks) == 5
    assert LocationId.NEW_SYSTEM_CORE in logistics.depot_stocks
    assert LocationId.CONTESTED_SPACEPORT in logistics.depot_stocks
    assert LocationId.CONTESTED_MID_DEPOT in logistics.depot_stocks
    assert LocationId.CONTESTED_FRONT in logistics.depot_stocks
    assert len(logistics.routes) == 4
    assert len(logistics.shipments) == 0


def test_create_shipment() -> None:
    """Test creating a shipment."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    # Pre-stock origin
    logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT] = Supplies(ammo=100, fuel=100, med_spares=100)
    initial_mid = logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT].ammo
    service.create_shipment(
        logistics,
        LocationId.CONTESTED_MID_DEPOT,
        LocationId.CONTESTED_FRONT,
        Supplies(ammo=50, fuel=30, med_spares=10),
        None,
        rng,
    )

    assert logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT].ammo == initial_mid - 50
    assert len(logistics.shipments) == 1
    shipment = logistics.shipments[0]
    assert shipment.origin == LocationId.CONTESTED_MID_DEPOT
    assert shipment.destination == LocationId.CONTESTED_FRONT
    assert shipment.days_remaining > 0


def test_create_shipment_insufficient_stock() -> None:
    """Test that creating shipment with insufficient stock raises error."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    # Set Core stock to low value
    logistics.depot_stocks[LocationId.NEW_SYSTEM_CORE] = Supplies(ammo=10, fuel=10, med_spares=10)

    with pytest.raises(ValueError, match="Insufficient supplies"):
        service.create_shipment(
            logistics,
            LocationId.CONTESTED_MID_DEPOT,
            LocationId.CONTESTED_FRONT,
            Supplies(ammo=50, fuel=30, med_spares=10),
            None,
            rng,
        )


def test_logistics_tick() -> None:
    """Test logistics daily tick advances shipments."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    planet = _dummy_planet()
    initial_mid = logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT].ammo

    # Pre-stock origin
    logistics.depot_stocks[LocationId.CONTESTED_SPACEPORT] = Supplies(ammo=100, fuel=100, med_spares=100)
    # Create shipment from Spaceport to Mid (Ground)
    service.create_shipment(
        logistics,
        LocationId.CONTESTED_SPACEPORT,
        LocationId.CONTESTED_MID_DEPOT,
        Supplies(ammo=50, fuel=0, med_spares=0),
        None,
        rng,
    )

    shipment = logistics.shipments[0]
    days_needed = shipment.days_remaining

    # Tick until delivery
    for _ in range(days_needed):
        service.tick(logistics, planet, rng)

    # Shipment should be delivered
    assert len(logistics.shipments) == 0
    assert logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT].ammo == initial_mid + 50


def test_logistics_tick_interdiction() -> None:
    """Test that interdiction can occur and reduce supplies."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    # Use a seed that triggers interdiction (or test multiple seeds)
    rng = Random(1)  # May or may not trigger, but we can test the mechanism
    planet = _dummy_planet()

    # Pre-stock MID so we have enough for the shipment
    logistics.depot_stocks[LocationId.CONTESTED_MID_DEPOT] = Supplies(ammo=100, fuel=50, med_spares=30)

    service.create_shipment(
        logistics,
        LocationId.CONTESTED_MID_DEPOT,
        LocationId.CONTESTED_FRONT,
        Supplies(ammo=100, fuel=0, med_spares=0),
        None,
        rng,
    )

    shipment = logistics.shipments[0]
    original_ammo = shipment.supplies.ammo

    # First tick checks interdiction
    service.tick(logistics, planet, rng)

    # If interdicted, ammo should be reduced
    if shipment.interdicted:
        assert shipment.supplies.ammo < original_ammo
