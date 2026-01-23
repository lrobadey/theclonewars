
import pytest
from random import Random
from clone_wars.engine.logistics import LogisticsState, CargoShip, ShipState, Shipment
from clone_wars.engine.services.logistics import LogisticsService
from clone_wars.engine.types import LocationId, Supplies, UnitStock

@pytest.fixture
def service():
    return LogisticsService()

@pytest.fixture
def rng():
    return Random(42)

def test_logistics_state_initialization():
    state = LogisticsState.new()
    assert len(state.ships) > 0
    assert "1" in state.ships
    ship = state.ships["1"]
    assert ship.location == LocationId.NEW_SYSTEM_CORE
    assert ship.state == ShipState.IDLE
    
    # Verify new 5-node locations exist in depots
    assert LocationId.NEW_SYSTEM_CORE in state.depot_stocks
    assert LocationId.CONTESTED_SPACEPORT in state.depot_stocks
    assert LocationId.CONTESTED_MID_DEPOT in state.depot_stocks

def test_cargo_ship_space_transit(service, rng):
    state = LogisticsState.new()
    # Setup: 1 Ship at Core (Default)
    ship = state.ships["1"]
    initial_core_ammo = state.depot_stocks[LocationId.NEW_SYSTEM_CORE].ammo
    payload = Supplies(ammo=100, fuel=50, med_spares=0)
    
    # 1. Create Shipment (Core -> Spaceport)
    # This should trigger _launch_cargo_ship
    service.create_shipment(
        state,
        LocationId.NEW_SYSTEM_CORE,
        LocationId.CONTESTED_SPACEPORT,
        payload,
        UnitStock(0,0,0),
        rng
    )
    
    # Verify Ship Loaded & Launched
    assert ship.state == ShipState.TRANSIT
    assert ship.supplies.ammo == 100
    assert ship.location == LocationId.NEW_SYSTEM_CORE # Origin
    assert ship.destination == LocationId.DEEP_SPACE # Next Hop
    
    # Verify Core Stock Deducted
    assert state.depot_stocks[LocationId.NEW_SYSTEM_CORE].ammo == initial_core_ammo - 100
    
    # 2. Tick 1: Travel to Deep Space
    # Assuming Core->Deep is 1 day
    service.tick(state, None, rng) # Planet is None for space tick mostly
    
    assert ship.location == LocationId.DEEP_SPACE
    assert ship.destination == LocationId.CONTESTED_SPACEPORT # Next Hop Updated
    assert ship.state == ShipState.TRANSIT
    
    # 3. Tick 2: Travel to Spaceport
    # Assuming Deep->Spaceport is 1 day
    service.tick(state, None, rng)
    
    assert ship.location == LocationId.CONTESTED_SPACEPORT
    assert ship.state == ShipState.IDLE # Should unload and idle
    assert ship.supplies.ammo == 0 # Unloaded
    
    # Verify Spaceport Stock Increased
    assert state.depot_stocks[LocationId.CONTESTED_SPACEPORT].ammo == 100

def test_ground_convoy_movement(service, rng):
    state = LogisticsState.new()
    # Setup: Stock at Spaceport for ground shipment
    state.depot_stocks[LocationId.CONTESTED_SPACEPORT] = Supplies(ammo=500, fuel=500, med_spares=500)
    
    payload = Supplies(ammo=100, fuel=0, med_spares=0)
    
    # 1. Create Shipment (Spaceport -> Mid)
    service.create_shipment(
        state,
        LocationId.CONTESTED_SPACEPORT,
        LocationId.CONTESTED_MID_DEPOT,
        payload,
        UnitStock(0,0,0),
        rng
    )
    
    # Verify Shipment Created
    assert len(state.shipments) == 1
    shipment = state.shipments[0]
    assert shipment.origin == LocationId.CONTESTED_SPACEPORT
    assert shipment.destination == LocationId.CONTESTED_MID_DEPOT
    
    # 2. Tick: Move Ground Convoy
    # Logic is simplified: 1 day travel?
    total_days = shipment.total_days
    for _ in range(total_days):
        service.tick(state, None, rng)
        
    # Verify Delivery
    assert len(state.shipments) == 0 # Delivered
    assert state.depot_stocks[LocationId.CONTESTED_MID_DEPOT].ammo == 100

def test_insufficient_capacity_raises_error(service, rng):
    """When no ships are available for a space leg, create_shipment should raise."""
    state = LogisticsState.new()
    # Occupy all ships
    for ship in state.ships.values():
        ship.state = ShipState.TRANSIT
        
    payload = Supplies(ammo=10, fuel=0, med_spares=0)
    
    # The new behavior raises immediately if no ship is available
    # This prevents stock from being deducted without dispatch happening
    import pytest
    with pytest.raises(ValueError, match="No idle cargo ship available"):
        service.create_shipment(
            state,
            LocationId.NEW_SYSTEM_CORE,
            LocationId.CONTESTED_SPACEPORT,
            payload,
            UnitStock(0,0,0),
            rng
        )
    
    # No order should be created
    assert len(state.active_orders) == 0
