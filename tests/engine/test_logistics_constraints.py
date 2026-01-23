import unittest
from random import Random

from clone_wars.engine.logistics import LogisticsState, ShipState
from clone_wars.engine.services.logistics import LogisticsService
from clone_wars.engine.types import (
    LocationId,
    PlanetState,
    Supplies,
    UnitStock,
    Objectives,
    ObjectiveStatus,
    EnemyForce,
)


class TestLogisticsConstraints(unittest.TestCase):
    def setUp(self):
        self.logistics_state = LogisticsState.new()
        self.planet_state = PlanetState(
            control=1.0,
            objectives=Objectives(
                foundry=ObjectiveStatus.SECURED,
                comms=ObjectiveStatus.SECURED,
                power=ObjectiveStatus.SECURED,
            ),
            enemy=EnemyForce(
                infantry=0,
                walkers=0,
                support=0,
                cohesion=0.0,
                fortification=0.0,
                reinforcement_rate=0.0,
                intel_confidence=1.0,
            ),
        )
        self.service = LogisticsService()
        self.rng = Random(1)

    def test_ship_capacity_limit(self):
        """Cargo ships should reject payloads that exceed capacity (no ship with capacity available)."""
        origin = LocationId.NEW_SYSTEM_CORE
        dest = LocationId.DEEP_SPACE
        supplies = Supplies(500, 0, 0)  # Ammo exceeds ship capacity (200)

        # With the new logic, we check capacity when finding an available ship.
        # If no ship can load the cargo, "No idle cargo ship available" is raised.
        with self.assertRaisesRegex(ValueError, "No idle cargo ship available"):
            self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)

    def test_no_idle_ship_available(self):
        """Launching from a location without idle ships should fail."""
        origin = LocationId.NEW_SYSTEM_CORE
        dest = LocationId.DEEP_SPACE
        supplies = Supplies(10, 0, 0)

        for ship in self.logistics_state.ships.values():
            ship.state = ShipState.TRANSIT

        with self.assertRaisesRegex(ValueError, "No idle cargo ship available"):
            self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)

    def test_ship_waypoint_to_spaceport(self):
        """Ships should waypoint through Deep Space en route to the spaceport."""
        origin = LocationId.NEW_SYSTEM_CORE
        dest = LocationId.CONTESTED_SPACEPORT
        supplies = Supplies(10, 0, 0)

        self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)
        ship = next(iter(self.logistics_state.ships.values()))
        self.assertEqual(ship.state, ShipState.TRANSIT)

        # First tick moves to Deep Space and immediately continues toward spaceport.
        self.service.tick(self.logistics_state, self.planet_state, self.rng)
        self.assertEqual(ship.location, LocationId.DEEP_SPACE)
        self.assertEqual(ship.destination, LocationId.CONTESTED_SPACEPORT)
        self.assertEqual(ship.state, ShipState.TRANSIT)

    def test_ship_arrives_and_unloads(self):
        """Ships should arrive at the spaceport and return to idle."""
        origin = LocationId.NEW_SYSTEM_CORE
        dest = LocationId.CONTESTED_SPACEPORT
        supplies = Supplies(10, 0, 0)

        self.service.create_shipment(self.logistics_state, origin, dest, supplies, None, self.rng)
        ship = next(iter(self.logistics_state.ships.values()))

        # Two ticks: Core -> Deep Space -> Spaceport
        self.service.tick(self.logistics_state, self.planet_state, self.rng)
        self.service.tick(self.logistics_state, self.planet_state, self.rng)

        self.assertEqual(ship.location, LocationId.CONTESTED_SPACEPORT)
        self.assertEqual(ship.state, ShipState.IDLE)
        self.assertEqual(ship.orders, [])


if __name__ == "__main__":
    unittest.main()
