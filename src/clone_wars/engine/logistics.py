"""Logistics system: depots, routes, and shipments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from clone_wars.engine.types import Supplies, UnitStock


class DepotNode(str, Enum):
    """Depot/location nodes in the logistics network."""

    CORE = "Core"
    MID_DEPOT = "Mid Depot"
    FORWARD_DEPOT = "Forward Depot"
    KEY_PLANET = "Key Planet"


@dataclass(slots=True)
class Route:
    """A route between two depots."""

    origin: DepotNode
    destination: DepotNode
    travel_days: int
    interdiction_risk: float  # 0.0 to 1.0, probability of interdiction per day


@dataclass(slots=True)
class Shipment:
    """A shipment in transit."""

    origin: DepotNode
    destination: DepotNode
    supplies: Supplies
    units: UnitStock
    days_remaining: int
    total_days: int  # Original travel time
    interdicted: bool = False


@dataclass(slots=True)
class LogisticsState:
    """Logistics network state."""

    depot_stocks: dict[DepotNode, Supplies]
    depot_units: dict[DepotNode, UnitStock]
    routes: list[Route]
    shipments: list[Shipment]

    @staticmethod
    def new() -> LogisticsState:
        """Create initial logistics state with default network."""
        routes = [
            Route(DepotNode.CORE, DepotNode.MID_DEPOT, travel_days=2, interdiction_risk=0.10),
            Route(DepotNode.MID_DEPOT, DepotNode.FORWARD_DEPOT, travel_days=3, interdiction_risk=0.15),
            Route(DepotNode.FORWARD_DEPOT, DepotNode.KEY_PLANET, travel_days=1, interdiction_risk=0.20),
        ]
        depot_stocks = {
            DepotNode.CORE: Supplies(ammo=500, fuel=400, med_spares=200),
            DepotNode.MID_DEPOT: Supplies(ammo=100, fuel=80, med_spares=40),
            DepotNode.FORWARD_DEPOT: Supplies(ammo=50, fuel=40, med_spares=20),
            DepotNode.KEY_PLANET: Supplies(ammo=0, fuel=0, med_spares=0),
        }
        depot_units = {
            DepotNode.CORE: UnitStock(infantry=0, walkers=0, support=0),
            DepotNode.MID_DEPOT: UnitStock(infantry=0, walkers=0, support=0),
            DepotNode.FORWARD_DEPOT: UnitStock(infantry=0, walkers=0, support=0),
            DepotNode.KEY_PLANET: UnitStock(infantry=0, walkers=0, support=0),
        }
        return LogisticsState(
            depot_stocks=depot_stocks,
            depot_units=depot_units,
            routes=routes,
            shipments=[],
        )

    def create_shipment(
        self,
        origin: DepotNode,
        destination: DepotNode,
        supplies: Supplies,
        rng: object,  # Random
        units: UnitStock | None = None,
    ) -> None:
        """Create a new shipment if route exists and origin has enough stock."""
        route = self._find_route(origin, destination)
        if route is None:
            raise ValueError(f"No route from {origin.value} to {destination.value}")

        if units is None:
            units = UnitStock(infantry=0, walkers=0, support=0)

        # Check stock availability
        stock = self.depot_stocks[origin]
        if stock.ammo < supplies.ammo or stock.fuel < supplies.fuel or stock.med_spares < supplies.med_spares:
            raise ValueError("Insufficient stock at origin depot")
        unit_stock = self.depot_units[origin]
        if (
            unit_stock.infantry < units.infantry
            or unit_stock.walkers < units.walkers
            or unit_stock.support < units.support
        ):
            raise ValueError("Insufficient unit stock at origin depot")

        # Deduct from origin
        self.depot_stocks[origin] = Supplies(
            ammo=stock.ammo - supplies.ammo,
            fuel=stock.fuel - supplies.fuel,
            med_spares=stock.med_spares - supplies.med_spares,
        )
        self.depot_units[origin] = UnitStock(
            infantry=unit_stock.infantry - units.infantry,
            walkers=unit_stock.walkers - units.walkers,
            support=unit_stock.support - units.support,
        )

        # Create shipment
        shipment = Shipment(
            origin=origin,
            destination=destination,
            supplies=supplies,
            units=units,
            days_remaining=route.travel_days,
            total_days=route.travel_days,
        )
        self.shipments.append(shipment)

    def _find_route(self, origin: DepotNode, destination: DepotNode) -> Route | None:
        """Find route from origin to destination."""
        for route in self.routes:
            if route.origin == origin and route.destination == destination:
                return route
        return None

    def tick(self, rng: object) -> None:
        """Advance logistics by one day: move shipments, check interdiction, deliver."""
        # Process each shipment
        completed: list[Shipment] = []
        for shipment in self.shipments:
            # Check interdiction (once per shipment, on first day)
            if not shipment.interdicted and shipment.days_remaining == shipment.total_days:
                route = self._find_route(shipment.origin, shipment.destination)
                if route and rng.random() < route.interdiction_risk:
                    shipment.interdicted = True
                    # Apply loss: 20-40% of supplies
                    loss_factor = 0.7 + (rng.random() * 0.2)  # 0.7 to 0.9 (20-40% loss)
                    shipment.supplies = Supplies(
                        ammo=int(shipment.supplies.ammo * loss_factor),
                        fuel=int(shipment.supplies.fuel * loss_factor),
                        med_spares=int(shipment.supplies.med_spares * loss_factor),
                    )

            shipment.days_remaining -= 1
            if shipment.days_remaining <= 0:
                # Deliver to destination
                dest_stock = self.depot_stocks[shipment.destination]
                self.depot_stocks[shipment.destination] = Supplies(
                    ammo=dest_stock.ammo + shipment.supplies.ammo,
                    fuel=dest_stock.fuel + shipment.supplies.fuel,
                    med_spares=dest_stock.med_spares + shipment.supplies.med_spares,
                )
                dest_units = self.depot_units[shipment.destination]
                self.depot_units[shipment.destination] = UnitStock(
                    infantry=dest_units.infantry + shipment.units.infantry,
                    walkers=dest_units.walkers + shipment.units.walkers,
                    support=dest_units.support + shipment.units.support,
                )
                completed.append(shipment)

        # Remove completed shipments
        for shipment in completed:
            self.shipments.remove(shipment)
