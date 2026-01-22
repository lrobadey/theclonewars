import unittest
from random import Random
from clone_wars.engine.types import LocationId, Supplies
from clone_wars.engine.logistics import LogisticsState, Route
from clone_wars.engine.services.logistics import LogisticsService

class TestLogisticsRouting(unittest.TestCase):
    def setUp(self):
        self.logistics_service = LogisticsService()
        self.state = LogisticsState.new()
        self.state.routes = [
            Route(LocationId.NEW_SYSTEM_CORE, LocationId.DEEP_SPACE, 1, 0.0),
            Route(LocationId.DEEP_SPACE, LocationId.CONTESTED_SPACEPORT, 1, 0.0),
            Route(LocationId.CONTESTED_SPACEPORT, LocationId.CONTESTED_MID_DEPOT, 1, 0.0),
            Route(LocationId.CONTESTED_MID_DEPOT, LocationId.CONTESTED_FRONT, 1, 0.0),
        ]
        self.rng = Random(42)

    def test_find_path_core_to_front(self):
        path = self.logistics_service._find_path(self.state, LocationId.NEW_SYSTEM_CORE, LocationId.CONTESTED_FRONT)
        expected = (
            LocationId.NEW_SYSTEM_CORE,
            LocationId.DEEP_SPACE,
            LocationId.CONTESTED_SPACEPORT,
            LocationId.CONTESTED_MID_DEPOT,
            LocationId.CONTESTED_FRONT
        )
        self.assertEqual(path, expected)

    def test_create_shipment_space_leg(self):
        # Dispatch from Core to Front
        self.logistics_service.create_shipment(
            self.state,
            LocationId.NEW_SYSTEM_CORE,
            LocationId.CONTESTED_FRONT,
            Supplies(10, 10, 0),
            None,
            self.rng
        )
        
        # Should have created an active order
        self.assertEqual(len(self.state.active_orders), 1)
        order = self.state.active_orders[0]
        self.assertEqual(order.status, "transit")
        self.assertEqual(order.final_destination, LocationId.CONTESTED_FRONT)
        
        # Should have loaded a ship
        ship = self.state.ships["1"]
        self.assertEqual(ship.state, "transit")
        self.assertEqual(ship.destination, LocationId.DEEP_SPACE) # Next hop
        self.assertEqual(len(ship.orders), 1)
        self.assertEqual(ship.orders[0], order)

if __name__ == '__main__':
    unittest.main()
