import pytest
from clone_wars.engine.state import GameState
from clone_wars.engine.types import UnitStock, Supplies
from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.production import ProductionJobType

def test_granular_trooper_shipment():
    """Verify shipments can handle non-squad-multiple trooper counts."""
    state = GameState.new()
    
    # Setup: Add exact number of troops to Core
    # We want to ship 13 troops. Ensure Core has enough.
    # Current GameState.new might init with 120 (6 squads).
    core_units = state.logistics.depot_units[DepotNode.CORE]
    # Reset to known state for test clarity
    state.logistics.depot_units[DepotNode.CORE] = UnitStock(infantry=100, walkers=0, support=0)
    
    # Create shipment of 13 infantry
    state.logistics_service.create_shipment(
        state.logistics,
        DepotNode.CORE,
        DepotNode.MID,
        Supplies(0, 0, 0),
        UnitStock(13, 0, 0),
        state.rng
    )
    
    # Process ticks until arrival (Core->Mid is usually 1-2 days)
    # Just tick enough times
    initial_mid = state.logistics.depot_units[DepotNode.MID].infantry
    
    # Route Core->Mid
    # We need to check route time or just tick.
    # We can inspect the shipment directly.
    assert len(state.logistics.shipments) == 1
    shipment = state.logistics.shipments[0]
    assert shipment.units.infantry == 13
    
    # Fast forward
    days = shipment.total_days
    for _ in range(days + 1):
        state.logistics_service.tick(state.logistics, state.rng)
        
    # Verify arrival
    new_mid = state.logistics.depot_units[DepotNode.MID].infantry
    assert new_mid == initial_mid + 13

def test_granular_production():
    """Verify production output is exact quantity, not multiplied by squad size."""
    state = GameState.new()
    state.production.jobs.clear()
    
    # Queue 7 infantry
    # Validates that we can queue '7' and get '7', not '7 * 20' = 140
    state.production.queue_job(ProductionJobType.INFANTRY, 7, DepotNode.CORE)
    
    # Force tick production
    # Capacity is default 3 factories * 1 slot = 3/day.
    # 7 units. Each unit takes 1 slot-day? 
    # Let's check production logic. 
    # "job.remaining -= 1; capacity_remaining -= 1"
    # So 1 unit quantity takes 1 capacity-point.
    # If capacity is 3, we can produce 3 units per day.
    # 7 units should take ceil(7/3) = 3 days.
    
    # Day 1: 3 completed? No, production logic:
    # "if job.remaining <= 0: completed.append..."
    # So it drains the job. It doesn't partial deliver.
    # Job starts with remaining=7.
    # Day 1: -3 => rem 4
    # Day 2: -3 => rem 1
    # Day 3: -1 => rem 0 => complete!
    
    initial_core_inf = state.logistics.depot_units[DepotNode.CORE].infantry
    
    completed = []
    for _ in range(3):
        out = state.production.tick()
        completed.extend(out)
        
    # Should be done now
    assert len(completed) == 1
    assert completed[0].quantity == 7
    
    # Apply output
    for out in completed:
        state._apply_production_output(out)
        
    final_core_inf = state.logistics.depot_units[DepotNode.CORE].infantry
    # If logic multiplies by SQUAD_SIZE(20), this would be +140. We want +7.
    assert final_core_inf == initial_core_inf + 7
