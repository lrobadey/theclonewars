"""Logistics service logic."""

from __future__ import annotations

from collections import deque
from random import Random

from clone_wars.engine.logistics import DepotNode, LogisticsState, Route, Shipment
from clone_wars.engine.types import Supplies, UnitStock


class LogisticsService:
    """Service for handling logistics operations."""

    def tick(self, state: LogisticsState, rng: Random) -> None:
        """Advance logistics by one day: move shipments, check interdiction, deliver."""
        # Process each shipment
        remaining_shipments: list[Shipment] = []
        for shipment in state.shipments:
            # Check interdiction (once per leg, on first day of that leg)
            if shipment.days_remaining == shipment.total_days:
                route = self._find_route(state, shipment.origin, shipment.destination)
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
                    dest_stock = state.depot_stocks[shipment.destination]
                    state.depot_stocks[shipment.destination] = Supplies(
                        ammo=dest_stock.ammo + shipment.supplies.ammo,
                        fuel=dest_stock.fuel + shipment.supplies.fuel,
                        med_spares=dest_stock.med_spares + shipment.supplies.med_spares,
                    )
                    dest_units = state.depot_units[shipment.destination]
                    state.depot_units[shipment.destination] = UnitStock(
                        infantry=dest_units.infantry + shipment.units.infantry,
                        walkers=dest_units.walkers + shipment.units.walkers,
                        support=dest_units.support + shipment.units.support,
                    )
                    continue
                # Depart immediately on next leg (no dwell time).
                shipment.leg_index += 1
                next_origin = shipment.origin
                next_destination = shipment.destination
                route = self._find_route(state, next_origin, next_destination)
                if route is None:
                    raise ValueError(
                        f"No route from {next_origin.value} to {next_destination.value}"
                    )
                shipment.total_days = route.travel_days
                shipment.days_remaining = route.travel_days
            remaining_shipments.append(shipment)

        # Keep only in-transit shipments for next tick
        state.shipments = remaining_shipments

    def create_shipment(
        self,
        state: LogisticsState,
        origin: DepotNode,
        destination: DepotNode,
        supplies: Supplies,
        units: UnitStock | None,
        rng: Random,
    ) -> None:
        """Create a new shipment if a path exists and origin has enough stock."""
        if origin == destination:
            raise ValueError("Shipment origin and destination must differ")

        path = self._find_path(state, origin, destination)
        if path is None or len(path) < 2:
            raise ValueError(f"No route from {origin.value} to {destination.value}")
        first_hop = path[1]
        route = self._find_route(state, origin, first_hop)
        if route is None:
            raise ValueError(f"No route from {origin.value} to {destination.value}")

        if units is None:
            units = UnitStock(infantry=0, walkers=0, support=0)

        # Check stock availability
        stock = state.depot_stocks[origin]
        if stock.ammo < supplies.ammo or stock.fuel < supplies.fuel or stock.med_spares < supplies.med_spares:
            raise ValueError("Insufficient stock at origin depot")
        unit_stock = state.depot_units[origin]
        if (
            unit_stock.infantry < units.infantry
            or unit_stock.walkers < units.walkers
            or unit_stock.support < units.support
        ):
            raise ValueError("Insufficient unit stock at origin depot")

        # Deduct from origin
        state.depot_stocks[origin] = Supplies(
            ammo=stock.ammo - supplies.ammo,
            fuel=stock.fuel - supplies.fuel,
            med_spares=stock.med_spares - supplies.med_spares,
        )
        state.depot_units[origin] = UnitStock(
            infantry=unit_stock.infantry - units.infantry,
            walkers=unit_stock.walkers - units.walkers,
            support=unit_stock.support - units.support,
        )

        # Create shipment
        shipment = Shipment(
            shipment_id=state.next_shipment_id,
            path=path,
            leg_index=0,
            supplies=supplies,
            units=units,
            days_remaining=route.travel_days,
            total_days=route.travel_days,
        )
        state.next_shipment_id += 1
        state.shipments.append(shipment)

    def _find_route(self, state: LogisticsState, origin: DepotNode, destination: DepotNode) -> Route | None:
        """Find route from origin to destination."""
        for route in state.routes:
            if route.origin == origin and route.destination == destination:
                return route
        return None

    def _find_path(self, state: LogisticsState, origin: DepotNode, destination: DepotNode) -> tuple[DepotNode, ...] | None:
        """Find a path from origin to destination across routes (BFS)."""
        if origin == destination:
            return (origin,)

        adjacency: dict[DepotNode, list[DepotNode]] = {node: [] for node in DepotNode}
        for route in state.routes:
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
