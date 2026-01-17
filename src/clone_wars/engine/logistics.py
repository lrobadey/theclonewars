"""Logistics system: depots, routes, and shipments."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from clone_wars.engine.types import Supplies, UnitStock

if TYPE_CHECKING:  # pragma: no cover
    from random import Random


class DepotNode(str, Enum):
    """Depot/location nodes in the logistics network."""

    CORE = "Core"
    MID = "Mid"
    FRONT = "Front"

    # Backward-compatible aliases (prefer MID/FRONT going forward).
    MID_DEPOT = "Mid"
    FORWARD_DEPOT = "Front"
    KEY_PLANET = "Front"

    @property
    def short_label(self) -> str:
        match self:
            case DepotNode.CORE:
                return "CORE"
            case DepotNode.MID:
                return "MID"
            case DepotNode.FRONT:
                return "FRONT"


STORAGE_RISK_PER_DAY: dict[DepotNode, float] = {
    DepotNode.CORE: 0.00,
    DepotNode.MID: 0.01,
    DepotNode.FRONT: 0.06,
}


STORAGE_LOSS_PCT_RANGE: dict[DepotNode, tuple[float, float]] = {
    DepotNode.CORE: (0.00, 0.00),
    DepotNode.MID: (0.05, 0.10),
    DepotNode.FRONT: (0.10, 0.20),
}


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

    shipment_id: int
    path: tuple[DepotNode, ...]
    leg_index: int
    supplies: Supplies
    units: UnitStock
    days_remaining: int
    total_days: int  # Original travel time
    interdicted: bool = False

    @property
    def origin(self) -> DepotNode:
        return self.path[self.leg_index]

    @property
    def destination(self) -> DepotNode:
        return self.path[self.leg_index + 1]

    @property
    def final_destination(self) -> DepotNode:
        return self.path[-1]


@dataclass(slots=True)
class LogisticsState:
    """Logistics network state."""

    depot_stocks: dict[DepotNode, Supplies]
    depot_units: dict[DepotNode, UnitStock]
    routes: list[Route]
    shipments: list[Shipment]
    next_shipment_id: int

    @staticmethod
    def new() -> LogisticsState:
        """Create initial logistics state with default network."""
        routes = [
            Route(DepotNode.CORE, DepotNode.MID, travel_days=2, interdiction_risk=0.10),
            Route(DepotNode.MID, DepotNode.FRONT, travel_days=4, interdiction_risk=0.18),
        ]
        depot_stocks = {
            DepotNode.CORE: Supplies(ammo=500, fuel=400, med_spares=200),
            DepotNode.MID: Supplies(ammo=100, fuel=80, med_spares=40),
            DepotNode.FRONT: Supplies(ammo=0, fuel=0, med_spares=0),
        }
        depot_units = {
            DepotNode.CORE: UnitStock(infantry=0, walkers=0, support=0),
            DepotNode.MID: UnitStock(infantry=0, walkers=0, support=0),
            DepotNode.FRONT: UnitStock(infantry=0, walkers=0, support=0),
        }
        return LogisticsState(
            depot_stocks=depot_stocks,
            depot_units=depot_units,
            routes=routes,
            shipments=[],
            next_shipment_id=1,
        )

    def create_shipment(
        self,
        origin: DepotNode,
        destination: DepotNode,
        supplies: Supplies,
        units: UnitStock | None,
        rng: Random,
    ) -> None:
        """Create a new shipment if a path exists and origin has enough stock."""
        if origin == destination:
            raise ValueError("Shipment origin and destination must differ")

        path = self._find_path(origin, destination)
        if path is None or len(path) < 2:
            raise ValueError(f"No route from {origin.value} to {destination.value}")
        first_hop = path[1]
        route = self._find_route(origin, first_hop)
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
            shipment_id=self.next_shipment_id,
            path=path,
            leg_index=0,
            supplies=supplies,
            units=units,
            days_remaining=route.travel_days,
            total_days=route.travel_days,
        )
        self.next_shipment_id += 1
        self.shipments.append(shipment)

    def _find_route(self, origin: DepotNode, destination: DepotNode) -> Route | None:
        """Find route from origin to destination."""
        for route in self.routes:
            if route.origin == origin and route.destination == destination:
                return route
        return None

    def _find_path(self, origin: DepotNode, destination: DepotNode) -> tuple[DepotNode, ...] | None:
        """Find a path from origin to destination across routes (BFS)."""
        if origin == destination:
            return (origin,)

        adjacency: dict[DepotNode, list[DepotNode]] = {node: [] for node in DepotNode}
        for route in self.routes:
            adjacency[route.origin].append(route.destination)

        queue: deque[DepotNode] = deque([origin])
        visited: set[DepotNode] = {origin}
        parent: dict[DepotNode, DepotNode] = {}

        while queue:
            node = queue.popleft()
            for nxt in adjacency.get(node, []):
                if nxt in visited:
                    continue
                visited.add(nxt)
                parent[nxt] = node
                if nxt == destination:
                    queue.clear()
                    break
                queue.append(nxt)

        if destination not in visited:
            return None

        rev: list[DepotNode] = [destination]
        while rev[-1] != origin:
            rev.append(parent[rev[-1]])
        rev.reverse()
        return tuple(rev)

    def tick(self, rng: Random) -> None:
        """Advance logistics by one day: move shipments, check interdiction, deliver."""
        # Process each shipment
        remaining_shipments: list[Shipment] = []
        for shipment in self.shipments:
            # Check interdiction each day (once per shipment).
            if not shipment.interdicted:
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
                if shipment.leg_index >= len(shipment.path) - 2:
                    # Deliver to final destination
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
                    continue
                # Depart immediately on next leg (no dwell time).
                shipment.leg_index += 1
                next_origin = shipment.origin
                next_destination = shipment.destination
                route = self._find_route(next_origin, next_destination)
                if route is None:
                    raise ValueError(
                        f"No route from {next_origin.value} to {next_destination.value}"
                    )
                shipment.total_days = route.travel_days
                shipment.days_remaining = route.travel_days
            remaining_shipments.append(shipment)

        # Keep only in-transit shipments for next tick
        self.shipments = remaining_shipments
