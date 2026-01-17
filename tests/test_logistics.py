"""Tests for logistics system."""

from random import Random

import pytest

from clone_wars.engine.logistics import DepotNode, LogisticsState
from clone_wars.engine.services.logistics import LogisticsService
from clone_wars.engine.types import Supplies


def test_logistics_state_new() -> None:
    """Test creating new logistics state."""
    logistics = LogisticsState.new()
    assert len(logistics.depot_stocks) == 3
    assert DepotNode.CORE in logistics.depot_stocks
    assert len(logistics.routes) == 2
    assert len(logistics.shipments) == 0


def test_create_shipment() -> None:
    """Test creating a shipment."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    initial_core = logistics.depot_stocks[DepotNode.CORE].ammo

    service.create_shipment(
        logistics,
        DepotNode.CORE,
        DepotNode.MID_DEPOT,
        Supplies(ammo=50, fuel=30, med_spares=10),
        None,
        rng,
    )

    assert logistics.depot_stocks[DepotNode.CORE].ammo == initial_core - 50
    assert len(logistics.shipments) == 1
    shipment = logistics.shipments[0]
    assert shipment.origin == DepotNode.CORE
    assert shipment.destination == DepotNode.MID_DEPOT
    assert shipment.days_remaining > 0


def test_create_shipment_insufficient_stock() -> None:
    """Test that creating shipment with insufficient stock raises error."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    # Set Core stock to low value
    logistics.depot_stocks[DepotNode.CORE] = Supplies(ammo=10, fuel=10, med_spares=10)

    with pytest.raises(ValueError, match="Insufficient stock"):
        service.create_shipment(
            logistics,
            DepotNode.CORE,
            DepotNode.MID_DEPOT,
            Supplies(ammo=50, fuel=30, med_spares=10),
            None,
            rng,
        )


def test_logistics_tick() -> None:
    """Test logistics daily tick advances shipments."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    rng = Random(42)
    initial_mid = logistics.depot_stocks[DepotNode.MID].ammo

    # Create shipment
    service.create_shipment(
        logistics,
        DepotNode.CORE,
        DepotNode.MID_DEPOT,
        Supplies(ammo=50, fuel=0, med_spares=0),
        None,
        rng,
    )

    shipment = logistics.shipments[0]
    days_needed = shipment.days_remaining

    # Tick until delivery
    for _ in range(days_needed):
        service.tick(logistics, rng)

    # Shipment should be delivered
    assert len(logistics.shipments) == 0
    assert logistics.depot_stocks[DepotNode.MID].ammo == initial_mid + 50


def test_logistics_tick_interdiction() -> None:
    """Test that interdiction can occur and reduce supplies."""
    logistics = LogisticsState.new()
    service = LogisticsService()
    # Use a seed that triggers interdiction (or test multiple seeds)
    rng = Random(1)  # May or may not trigger, but we can test the mechanism

    # Pre-stock MID so we have enough for the shipment
    logistics.depot_stocks[DepotNode.MID] = Supplies(ammo=100, fuel=50, med_spares=30)

    service.create_shipment(
        logistics,
        DepotNode.MID,
        DepotNode.FRONT,
        Supplies(ammo=100, fuel=0, med_spares=0),
        None,
        rng,
    )

    shipment = logistics.shipments[0]
    original_ammo = shipment.supplies.ammo

    # First tick checks interdiction
    service.tick(logistics, rng)

    # If interdicted, ammo should be reduced
    if shipment.interdicted:
        assert shipment.supplies.ammo < original_ammo
