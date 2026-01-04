"""Comprehensive tests for logistics system."""

from random import Random

import pytest

from clone_wars.engine.logistics import DepotNode, LogisticsState, Route, Shipment
from clone_wars.engine.types import Supplies, UnitStock


def test_logistics_initial_state() -> None:
    """Test initial logistics state structure."""
    logistics = LogisticsState.new()

    # Verify all depots exist
    assert DepotNode.CORE in logistics.depot_stocks
    assert DepotNode.MID_DEPOT in logistics.depot_stocks
    assert DepotNode.FORWARD_DEPOT in logistics.depot_stocks
    assert DepotNode.KEY_PLANET in logistics.depot_stocks

    # Verify initial stocks are non-negative
    for depot, stock in logistics.depot_stocks.items():
        assert stock.ammo >= 0
        assert stock.fuel >= 0
        assert stock.med_spares >= 0

    # Verify routes exist
    assert len(logistics.routes) == 3
    for route in logistics.routes:
        assert route.origin in DepotNode
        assert route.destination in DepotNode
        assert route.travel_days > 0
        assert 0.0 <= route.interdiction_risk <= 1.0


def test_create_shipment_all_supplies() -> None:
    """Test creating shipment with all supply types."""
    logistics = LogisticsState.new()
    rng = Random(42)
    initial_core = logistics.depot_stocks[DepotNode.CORE]

    logistics.create_shipment(
        DepotNode.CORE,
        DepotNode.MID_DEPOT,
        Supplies(ammo=50, fuel=40, med_spares=20),
        rng=rng,
    )

    # Verify stock deducted
    new_core = logistics.depot_stocks[DepotNode.CORE]
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
    rng = Random(42)

    with pytest.raises(ValueError, match="No route"):
        logistics.create_shipment(
            DepotNode.KEY_PLANET,
            DepotNode.CORE,  # Reverse route doesn't exist
            Supplies(ammo=10, fuel=10, med_spares=10),
            rng=rng,
        )


def test_create_shipment_partial_shortage() -> None:
    """Test creating shipment with partial stock shortage."""
    logistics = LogisticsState.new()
    rng = Random(42)
    logistics.depot_stocks[DepotNode.CORE] = Supplies(ammo=100, fuel=5, med_spares=100)

    with pytest.raises(ValueError, match="Insufficient stock"):
        logistics.create_shipment(
            DepotNode.CORE,
            DepotNode.MID_DEPOT,
            Supplies(ammo=50, fuel=10, med_spares=50),  # fuel insufficient
            rng=rng,
        )


def test_multiple_shipments() -> None:
    """Test multiple shipments in transit simultaneously."""
    logistics = LogisticsState.new()
    rng = Random(42)

    # Create multiple shipments
    logistics.create_shipment(
        DepotNode.CORE,
        DepotNode.MID_DEPOT,
        Supplies(ammo=50, fuel=0, med_spares=0),
        rng=rng,
    )
    logistics.create_shipment(
        DepotNode.CORE,
        DepotNode.MID_DEPOT,
        Supplies(ammo=30, fuel=20, med_spares=0),
        rng=rng,
    )

    assert len(logistics.shipments) == 2
    assert logistics.shipments[0].origin == DepotNode.CORE
    assert logistics.shipments[1].origin == DepotNode.CORE


def test_shipment_delivery_chain() -> None:
    """Test shipment traveling through multiple depots."""
    logistics = LogisticsState.new()
    rng = Random(42)
    initial_key = logistics.depot_stocks[DepotNode.KEY_PLANET].ammo

    # Create shipment from Core to Key Planet (via Mid and Forward)
    # First: Core -> Mid
    logistics.create_shipment(
        DepotNode.CORE,
        DepotNode.MID_DEPOT,
        Supplies(ammo=100, fuel=0, med_spares=0),
        rng=rng,
    )

    shipment = logistics.shipments[0]
    days_to_mid = shipment.days_remaining

    # Advance to Mid Depot
    for _ in range(days_to_mid):
        logistics.tick(rng)

    assert len(logistics.shipments) == 0
    mid_stock = logistics.depot_stocks[DepotNode.MID_DEPOT].ammo

    # Create shipment from Mid -> Forward
    logistics.create_shipment(
        DepotNode.MID_DEPOT,
        DepotNode.FORWARD_DEPOT,
        Supplies(ammo=50, fuel=0, med_spares=0),
        rng=rng,
    )

    shipment = logistics.shipments[0]
    days_to_forward = shipment.days_remaining

    # Advance to Forward Depot
    for _ in range(days_to_forward):
        logistics.tick(rng)

    # Create shipment from Forward -> Key Planet
    logistics.create_shipment(
        DepotNode.FORWARD_DEPOT,
        DepotNode.KEY_PLANET,
        Supplies(ammo=30, fuel=0, med_spares=0),
        rng=rng,
    )

    shipment = logistics.shipments[0]
    days_to_key = shipment.days_remaining

    # Advance to Key Planet
    for _ in range(days_to_key):
        logistics.tick(rng)

    # Verify final delivery
    assert logistics.depot_stocks[DepotNode.KEY_PLANET].ammo == initial_key + 30


def test_interdiction_probability() -> None:
    """Test that interdiction occurs with correct probability over many runs."""
    logistics = LogisticsState.new()

    # Use route with high interdiction risk
    forward_to_key_route = next(
        r for r in logistics.routes
        if r.origin == DepotNode.FORWARD_DEPOT and r.destination == DepotNode.KEY_PLANET
    )
    assert forward_to_key_route.interdiction_risk > 0.1  # Should be 0.20

    interdicted_count = 0
    total_runs = 100

    for seed in range(total_runs):
        logistics = LogisticsState.new()
        rng = Random(seed)
        logistics.create_shipment(
            DepotNode.FORWARD_DEPOT,
            DepotNode.KEY_PLANET,
            Supplies(ammo=100, fuel=0, med_spares=0),
            rng=rng,
        )
        logistics.tick(rng)
        if logistics.shipments[0].interdicted:
            interdicted_count += 1

    # With 20% risk over 100 runs, we should see some interdictions
    # (not testing exact probability, just that mechanism works)
    assert interdicted_count > 0  # Should have at least some interdictions


def test_interdiction_supply_loss() -> None:
    """Test that interdiction reduces supplies correctly."""
    logistics = LogisticsState.new()
    # Find a seed that triggers interdiction
    for seed in range(100):
        logistics = LogisticsState.new()
        rng = Random(seed)
        original_ammo = 100
        logistics.create_shipment(
            DepotNode.FORWARD_DEPOT,
            DepotNode.KEY_PLANET,
            Supplies(ammo=original_ammo, fuel=50, med_spares=30),
            rng=rng,
        )
        logistics.tick(rng)
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
    rng = Random(42)

    logistics.create_shipment(
        DepotNode.CORE,
        DepotNode.MID_DEPOT,
        Supplies(ammo=50, fuel=0, med_spares=0),
        rng=rng,
    )

    shipment = logistics.shipments[0]
    total_days = shipment.total_days
    assert total_days > 0
    assert shipment.days_remaining == total_days

    # After one tick
    logistics.tick(rng)
    assert shipment.days_remaining == total_days - 1


def test_empty_logistics_tick() -> None:
    """Test that tick works with no shipments."""
    logistics = LogisticsState.new()
    rng = Random(42)

    # Should not raise error
    logistics.tick(rng)
    assert len(logistics.shipments) == 0


def test_shipment_delivery_preserves_other_stocks() -> None:
    """Test that delivery doesn't affect other supply types incorrectly."""
    logistics = LogisticsState.new()
    rng = Random(42)
    initial_mid = logistics.depot_stocks[DepotNode.MID_DEPOT]

    logistics.create_shipment(
        DepotNode.CORE,
        DepotNode.MID_DEPOT,
        Supplies(ammo=50, fuel=0, med_spares=0),
        rng=rng,
    )

    shipment = logistics.shipments[0]
    days = shipment.days_remaining

    for _ in range(days):
        logistics.tick(rng)

    final_mid = logistics.depot_stocks[DepotNode.MID_DEPOT]
    # Only ammo should increase
    assert final_mid.ammo == initial_mid.ammo + 50
    assert final_mid.fuel == initial_mid.fuel
    assert final_mid.med_spares == initial_mid.med_spares


def test_unit_shipment_delivery() -> None:
    """Test that unit shipments deliver to depot unit stock."""
    logistics = LogisticsState.new()
    rng = Random(7)
    initial_units = logistics.depot_units[DepotNode.MID_DEPOT]
    logistics.depot_units[DepotNode.CORE] = UnitStock(infantry=10, walkers=5, support=4)

    logistics.create_shipment(
        DepotNode.CORE,
        DepotNode.MID_DEPOT,
        Supplies(ammo=0, fuel=0, med_spares=0),
        UnitStock(infantry=4, walkers=1, support=2),
        rng=rng,
    )

    shipment = logistics.shipments[0]
    for _ in range(shipment.days_remaining):
        logistics.tick(rng)

    final_units = logistics.depot_units[DepotNode.MID_DEPOT]
    assert final_units.infantry == initial_units.infantry + 4
    assert final_units.walkers == initial_units.walkers + 1
    assert final_units.support == initial_units.support + 2
