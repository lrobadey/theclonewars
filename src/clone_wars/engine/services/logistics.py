"""Logistics service logic."""

from __future__ import annotations

from collections import deque
from random import Random

from clone_wars.engine.logistics import LogisticsState, Route, Shipment
from clone_wars.engine.types import LocationId, PlanetState, Supplies, UnitStock


class LogisticsService:
    """Service for handling logistics operations."""

    def tick(self, state: LogisticsState, planet: PlanetState, rng: Random) -> None:
        """Advance logistics by one day: move shipments, check interdiction, deliver."""
        # Process each shipment
        remaining_shipments: list[Shipment] = []
        for shipment in state.shipments:
            # Check interdiction (once per leg, on first day of that leg)
            if shipment.days_remaining == shipment.total_days:
                route = self._find_route(state, shipment.origin, shipment.destination)
                risk = 0.0
                if route:
                    risk = self._calculate_dynamic_risk(route, state.shipments, planet)
                
                if rng.random() < risk:
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
        origin: LocationId,
        destination: LocationId,
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

    def _find_route(self, state: LogisticsState, origin: LocationId, destination: LocationId) -> Route | None:
        """Find route from origin to destination."""
        for route in state.routes:
            if route.origin == origin and route.destination == destination:
                return route
        return None

    def _find_path(self, state: LogisticsState, origin: LocationId, destination: LocationId) -> tuple[LocationId, ...] | None:
        """Find a path from origin to destination across routes (BFS)."""
        if origin == destination:
            return (origin,)

        adjacency: dict[LocationId, list[LocationId]] = {node: [] for node in LocationId}
        for route in state.routes:
            adjacency[route.origin].append(route.destination)

        queue: deque[LocationId] = deque([origin])
        visited: set[LocationId] = {origin}
        parent: dict[LocationId, LocationId] = {}

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

        rev: list[LocationId] = [destination]
        while rev[-1] != origin:
            rev.append(parent[rev[-1]])
        rev.reverse()
        return tuple(rev)

    def _calculate_dynamic_risk(
        self, route: Route, shipments: list[Shipment], planet: PlanetState
    ) -> float:
        """Calculate interdiction risk based on traffic, intel, and control."""
        base_risk = route.interdiction_risk

        # Traffic penalty: +2% risk per OTHER active shipment on this specific leg
        # (Current shipment is already in the list, so we might count is here, 
        # but the risk usually applies to the group. Let's count all on this leg.)
        traffic_count = sum(
            1
            for s in shipments
            if s.days_remaining > 0
            and s.origin == route.origin
            and s.destination == route.destination
        )
        # Using a simple linear scaling for now.
        # Ensure we don't double count the shipment itself if it's already in the list (it is).
        # But 'traffic' implies volume. If alone, traffic is 1.
        traffic_penalty = max(0.0, (traffic_count - 1) * 0.02)

        # Enemy Intel: Scale up risk if enemy knows our moves
        intel_penalty = planet.enemy.intel_confidence * 0.20

        # Control: Low control increases risk
        control_penalty = (1.0 - planet.control) * 0.15

        total_risk = base_risk + traffic_penalty + intel_penalty + control_penalty
        return min(0.95, max(0.0, total_risk))
