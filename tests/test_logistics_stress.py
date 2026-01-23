import unittest
from random import Random
from clone_wars.engine.types import LocationId, PlanetState, Supplies, UnitStock, Objectives, ObjectiveStatus, EnemyForce
from clone_wars.engine.logistics import LogisticsState, Route
from clone_wars.engine.services.logistics import LogisticsService

class TestLogisticsStress(unittest.TestCase):
    def setUp(self):
        self.logistics_service = LogisticsService()
        self.state = LogisticsState.new()
        
        # Override stock for clean test
        self.state.depot_stocks[LocationId.NEW_SYSTEM_CORE] = Supplies(1000, 1000, 1000)
        self.state.depot_stocks[LocationId.CONTESTED_FRONT] = Supplies(0, 0, 0)
        
        # Mock planet need for tick()
        self.planet = PlanetState(
             objectives=Objectives(ObjectiveStatus.ENEMY, ObjectiveStatus.ENEMY, ObjectiveStatus.ENEMY),
             enemy=EnemyForce(0,0,0,0,0,0,0),
             control=0.5
        )
        self.rng = Random(42)

    def test_end_to_end_delivery(self):
        """
        Scenario:
        Day 0: Dispatch 100 Ammo from Core -> Front.
        Days 1+: Tick loop with physical leg-by-leg delivery.
        
        NEW BEHAVIOR: Goods physically travel through each waypoint:
        - Tick 1: Arrive Deep Space, immediately re-dispatch to Spaceport
        - Tick 2: Arrive Spaceport, create ground convoy to Mid  
        - Tick 3: Ground convoy arrives at Mid, create convoy to Front
        - Tick 4: Ground convoy arrives at Front
        
        Note: The dispatch for the next leg happens in the same tick as arrival,
        so goods don't "sit" at waypoints waiting for next day.
        """
        
        # --- Day 0: Dispatch ---
        print("\n[Day 0] Dispatching Shipment...")
        self.logistics_service.create_shipment(
            self.state,
            LocationId.NEW_SYSTEM_CORE,
            LocationId.CONTESTED_FRONT,
            Supplies(100, 0, 0),
            None,
            self.rng
        )
        
        # Verify initial state
        self.assertEqual(self.state.depot_stocks[LocationId.NEW_SYSTEM_CORE].ammo, 900)
        self.assertEqual(len(self.state.active_orders), 1)
        order = self.state.active_orders[0]
        self.assertEqual(order.status, "transit")
        self.assertEqual(order.final_destination, LocationId.CONTESTED_FRONT)
        
        ship = self.state.ships["1"]
        self.assertEqual(ship.destination, LocationId.DEEP_SPACE)
        
        # --- Tick 1: Ship arrives at Deep Space, immediately re-dispatches ---
        print("[Tick 1] Ship Core -> Deep Space, then re-dispatch to Spaceport...")
        self.logistics_service.tick(self.state, self.planet, self.rng, current_day=1)
        
        # Ship has arrived at Deep Space AND been re-dispatched to Spaceport
        self.assertEqual(ship.location, LocationId.DEEP_SPACE)
        self.assertEqual(ship.state.value, "transit")  # Already in transit again
        self.assertEqual(ship.destination, LocationId.CONTESTED_SPACEPORT)
        
        # Goods passed through Deep Space (depot shows 0 because they were picked up again)
        # Note: the order is on the ship again, so depot is empty
        self.assertEqual(self.state.depot_stocks[LocationId.DEEP_SPACE].ammo, 0)
        
        # --- Tick 2: Ship arrives at Spaceport ---
        print("[Tick 2] Ship arrives at Spaceport, ground convoy starts...")
        self.logistics_service.tick(self.state, self.planet, self.rng, current_day=2)
        
        # Ship arrived at Spaceport, unloaded
        self.assertEqual(ship.location, LocationId.CONTESTED_SPACEPORT)
        self.assertEqual(ship.state.value, "idle")
        
        # Ground convoy should be in transit to Mid
        self.assertEqual(order.status, "transit")
        self.assertEqual(len(self.state.shipments), 1)
        convoy = self.state.shipments[0]
        self.assertEqual(convoy.destination, LocationId.CONTESTED_MID_DEPOT)
        
        # --- Tick 3: Ground convoy arrives at Mid, new convoy to Front ---
        print("[Tick 3] Convoy arrives at Mid, new convoy to Front...")
        self.logistics_service.tick(self.state, self.planet, self.rng, current_day=3)
        
        # Order should be in transit to Front
        self.assertEqual(order.status, "transit")
        # New convoy created for Mid->Front
        self.assertEqual(len(self.state.shipments), 1)
        convoy = self.state.shipments[0]
        self.assertEqual(convoy.destination, LocationId.CONTESTED_FRONT)
        
        # --- Tick 4: Ground convoy arrives at Front ---
        print("[Tick 4] Convoy arrives at Front...")
        self.logistics_service.tick(self.state, self.planet, self.rng, current_day=4)
        
        # Order should be complete
        self.assertEqual(order.status, "complete")
        self.assertEqual(order.current_location, LocationId.CONTESTED_FRONT)
        
        # Stockpile check
        front_stock = self.state.depot_stocks[LocationId.CONTESTED_FRONT]
        self.assertEqual(front_stock.ammo, 100)
        
        # No more shipments in transit
        self.assertEqual(len(self.state.shipments), 0)
        
        print("[Audit] Success! 100 Ammo delivered to Front via physical supply chain in 4 ticks.")

if __name__ == '__main__':
    unittest.main()
