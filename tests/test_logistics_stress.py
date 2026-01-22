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
        Day 1-4: Tick loop.
        Goal: 100 Ammo arrives at Front without loss.
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
        
        # Verify initial state:
        # - Core Stock reduced
        self.assertEqual(self.state.depot_stocks[LocationId.NEW_SYSTEM_CORE].ammo, 900)
        # - Order Created
        self.assertEqual(len(self.state.active_orders), 1)
        order = self.state.active_orders[0]
        self.assertEqual(order.status, "transit")
        # - Ship Loaded
        ship = self.state.ships["1"]
        self.assertEqual(ship.orders[0], order)
        self.assertEqual(ship.destination, LocationId.DEEP_SPACE) # First Hop
        
        # --- Day 1: Space Transit (Core -> Deep) ---
        print("[Day 1] Ticking (Space Transit)...")
        self.logistics_service.tick(self.state, self.planet, self.rng)
        
        # Ship should be at DEEP SPACE (1 day travel)
        # Check auto-forwarding logic for next leg (Deep -> Spaceport)
        # The service tick handles arrival AND departure if auto-forwarding logic exists
        # In our implementation, Deep Space arrival triggers auto-forward to Spaceport
        self.assertEqual(ship.location, LocationId.DEEP_SPACE)
        self.assertEqual(ship.state, "transit")
        self.assertEqual(ship.destination, LocationId.CONTESTED_SPACEPORT)
        
        # --- Day 2: Arrival at Spaceport & Handoff ---
        print("[Day 2] Ticking (Arrival Spaceport)...")
        self.logistics_service.tick(self.state, self.planet, self.rng)
        
        # Ship arrived at Spaceport
        self.assertEqual(ship.location, LocationId.CONTESTED_SPACEPORT)
        # Ship should be empty (unloaded)
        self.assertEqual(len(ship.orders), 0)
        self.assertEqual(ship.state, "idle")
        
        # Ground Shipment should be created (Spaceport -> Mid)
        self.assertEqual(len(self.state.shipments), 1)
        convoy = self.state.shipments[0]
        print(f"DEBUG: Convoy State: {convoy}")
        print(f"DEBUG: Convoy Path: {[p.value for p in convoy.path]}")
        print(f"DEBUG: Convoy Leg Index: {convoy.leg_index}")
        self.assertEqual(convoy.orders[0], order)
        self.assertEqual(convoy.destination, LocationId.CONTESTED_MID_DEPOT)
        
        # --- Day 3: Convoy at Mid Depot ---
        print("[Day 3] Ticking (Arrival Mid/Transit Front)...")
        self.logistics_service.tick(self.state, self.planet, self.rng)
        
        # Convoy logic: If creates new leg, shipment object persists but leg_index increments
        # Leg 0 was Spaceport -> Mid
        # Leg 1 should be Mid -> Front
        self.assertEqual(convoy.leg_index, 1)
        self.assertEqual(convoy.destination, LocationId.CONTESTED_FRONT)
        
        # --- Day 4: Arrival at Front ---
        print("[Day 4] Ticking (Arrival Front)...")
        self.logistics_service.tick(self.state, self.planet, self.rng)
        
        # Order should be complete
        self.assertEqual(order.status, "complete")
        self.assertEqual(order.current_location, LocationId.CONTESTED_FRONT)
        
        # Stockpile check
        front_stock = self.state.depot_stocks[LocationId.CONTESTED_FRONT]
        self.assertEqual(front_stock.ammo, 100)
        
        print("[Audit] Success! 100 Ammo delivered to Front.")

if __name__ == '__main__':
    unittest.main()
