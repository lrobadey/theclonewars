import unittest
from random import Random
from clone_wars.engine.logistics import LogisticsState, Route
from clone_wars.engine.services.logistics import LogisticsService
from clone_wars.engine.types import (
    LocationId, 
    PlanetState, 
    Supplies, 
    UnitStock, 
    Objectives, 
    ObjectiveStatus, 
    EnemyForce
)

class TestLogisticsConstraints(unittest.TestCase):
    def setUp(self):
        self.logistics_state = LogisticsState.new()
        self.logistics_state.daily_port_capacity = 2
        self.logistics_state.total_hull_pool = 10
        self.logistics_state.used_hull_capacity = 0
        self.logistics_state.convoys_launched_today = 0
        
        self.planet_state = PlanetState(
            control=1.0,
            objectives=Objectives(
                foundry=ObjectiveStatus.SECURED,
                comms=ObjectiveStatus.SECURED,
                power=ObjectiveStatus.SECURED
            ),
            enemy=EnemyForce(
                infantry=0,
                walkers=0,
                support=0,
                cohesion=0.0,
                fortification=0.0,
                reinforcement_rate=0.0,
                intel_confidence=1.0
            )
        )
        self.service = LogisticsService()
        self.rng = Random(1)

    def test_port_capacity_limit(self):
        """Test that we cannot launch more convoys than dail capacity."""
        origin = LocationId.NEW_SYSTEM_CORE
        dest = LocationId.DEEP_SPACE_A # Valid route
        supplies = Supplies(10, 0, 0)
        
        # Launch 1
        self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)
        self.assertEqual(self.logistics_state.convoys_launched_today, 1)
        
        # Launch 2
        self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)
        self.assertEqual(self.logistics_state.convoys_launched_today, 2)
        
        # Launch 3 (Should fail)
        with self.assertRaisesRegex(ValueError, "Daily port capacity reached"):
            self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)

    def test_hull_pool_limit(self):
        """Test that we cannot launch if hull pool is empty."""
        self.logistics_state.daily_port_capacity = 100 # Remove port limit for this test
        self.logistics_state.total_hull_pool = 3
        
        origin = LocationId.NEW_SYSTEM_CORE
        dest = LocationId.DEEP_SPACE_A
        supplies = Supplies(10, 0, 0)
        
        # Use all hulls
        self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)
        self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)
        self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)
        
        self.assertEqual(self.logistics_state.used_hull_capacity, 3)
        
        # Try one more
        with self.assertRaisesRegex(ValueError, "Hull Pool depleted"):
            self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)

    def test_daily_reset(self):
        """Test that daily port counts reset on tick."""
        origin = LocationId.NEW_SYSTEM_CORE
        dest = LocationId.DEEP_SPACE_A
        supplies = Supplies(10, 0, 0)
        
        self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)
        self.assertEqual(self.logistics_state.convoys_launched_today, 1)
        
        self.service.tick(self.logistics_state, self.planet_state, self.rng)
        
        self.assertEqual(self.logistics_state.convoys_launched_today, 0)

    def test_hull_return_on_delivery(self):
        """Test that hull capacity is freed when shipment arrives."""
        origin = LocationId.NEW_SYSTEM_CORE
        dest = LocationId.DEEP_SPACE_A
        supplies = Supplies(10, 0, 0)
        
        # Set route travel time to 1 day
        for route in self.logistics_state.routes:
            if route.origin == origin and route.destination == dest:
                route.travel_days = 1
                
        self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)
        self.assertEqual(self.logistics_state.used_hull_capacity, 1)
        
        # This tick should deliver the shipment
        self.service.tick(self.logistics_state, self.planet_state, self.rng)
        
        self.assertEqual(len(self.logistics_state.shipments), 0)
        self.assertEqual(self.logistics_state.used_hull_capacity, 0)

if __name__ == "__main__":
    unittest.main()
