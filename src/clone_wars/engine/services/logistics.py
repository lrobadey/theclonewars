"""Logistics service logic."""

from __future__ import annotations

from collections import deque
from random import Random

from clone_wars.engine.logistics import CargoShip, LogisticsState, Route, Shipment, ShipState, TransitLogEntry, TransportOrder
from clone_wars.engine.types import LocationId, PlanetState, Supplies, UnitStock


class LogisticsService:
    """Service for handling logistics operations."""

    def tick(self, state: LogisticsState, planet: PlanetState, rng: Random, current_day: int = 0) -> None:
        """Advance logistics by one day: move ships and ground convoys."""
        
        # 1. Snapshot ground shipments (prevent immediate move of spawned convoys)
        existing_shipments = list(state.shipments)

        # 2. Update Cargo Ships (Space Network)
        for ship in state.ships.values():
            self._tick_ship(ship, state, planet, rng, current_day)
            
        # 3. Update Ground Shipments (Planetary Network)
        self._tick_ground_convoys(state, planet, rng, existing_shipments)

        # 4. Dispatch Pending Orders at Hubs
        self._dispatch_pending_orders(state, rng, current_day)
    
    def _log_event(self, state: LogisticsState, day: int, message: str, event_type: str) -> None:
        """Add a transit log entry (prepends to keep most recent first)."""
        entry = TransitLogEntry(day=day, message=message, event_type=event_type)
        state.transit_log.insert(0, entry)
        # Keep log trimmed to last 20 entries
        if len(state.transit_log) > 20:
            state.transit_log = state.transit_log[:20]

    def _tick_ship(self, ship: CargoShip, state: LogisticsState, planet: PlanetState, rng: Random, current_day: int = 0) -> None:
        """Process a single cargo ship's daily status."""
        if ship.state != ShipState.TRANSIT:
            return

        ship.days_remaining -= 1
        if ship.days_remaining <= 0:
            # Arrival at destination
            arrived_at = ship.destination
            ship.location = ship.destination
            ship.state = ShipState.IDLE
            ship.destination = None
            ship.days_remaining = 0

            # Log arrival
            loc_name = arrived_at.value.upper().replace("_", " ") if arrived_at else "UNKNOWN"
            self._log_event(state, current_day, f"{ship.name} arrived at {loc_name}", "arrived")

            # Unload ship and process orders - goods land at this depot
            # This makes goods VISIBLE at waypoints (Deep Space, Spaceport, etc.)
            self._arrive_at_location(state, ship.location, ship.orders, rng)
            
            # Clear ship payload
            ship.orders = []

    def _tick_ground_convoys(self, state: LogisticsState, planet: PlanetState, rng: Random, current_shipments: list[Shipment]) -> None:
        """Process ground convoys. NOTE: Iterates current_shipments snapshot (not state.shipments directly)."""
        
        # We REBUILD state.shipments. 
        # Any new shipments added during _tick_ship (e.g. by create_shipment) are ALREADY in state.shipments.
        # We must preserve them but NOT tick them if they are not in current_shipments.
        
        # Actually, simpler approach:
        # Loop through snapshot. Update them.
        # The objects in snapshot ARE the objects in state.shipments (references).
        # We just need to make sure we don't tick objects NOT in snapshot.
        
        # Set of IDs to process
        ids_to_tick = {s.shipment_id for s in current_shipments}
        
        active_list = []
        
        # Iterate over the MASTER list (which might have new items)
        for shipment in state.shipments:
            if shipment.shipment_id in ids_to_tick:
                # Process this shipment
                shipment.days_remaining -= 1
                if shipment.days_remaining <= 0:
                    # Arrival at the next leg's destination
                    self._arrive_at_location(state, shipment.destination, shipment.orders, rng)
                    # Shipment is done (removed from active list)
                else:
                    active_list.append(shipment)
            else:
                # Newly added shipment (untouched this tick)
                active_list.append(shipment)
                
        state.shipments = active_list

    def _arrive_at_location(
        self,
        state: LogisticsState,
        location: LocationId,
        orders: list[TransportOrder],
        rng: Random
    ) -> None:
        """Process arrival of goods at a node. Goods are ALWAYS added to depot stock here."""
        stock = state.depot_stocks[location]
        units_stock = state.depot_units[location]

        for order in orders:
            order.current_location = location
            # Clear transit tracking - goods are now at depot
            order.in_transit_leg = None
            order.carrier_id = None
            
            # Add to Stockpile regardless of whether it's the final destination
            # This ensures items are VISIBLE at the hub before being picked up again
            state.depot_stocks[location] = Supplies(
                ammo=stock.ammo + order.supplies.ammo,
                fuel=stock.fuel + order.supplies.fuel,
                med_spares=stock.med_spares + order.supplies.med_spares,
            )
            state.depot_units[location] = UnitStock(
                infantry=units_stock.infantry + order.units.infantry,
                walkers=units_stock.walkers + order.units.walkers,
                support=units_stock.support + order.units.support
            )
            
            if location == order.final_destination:
                order.status = "complete"
            else:
                # Wait for next tick's _dispatch_pending_orders to move to next leg
                order.status = "pending"

            # Refresh local references as we iterate
            stock = state.depot_stocks[location]
            units_stock = state.depot_units[location]

    def _dispatch_pending_orders(self, state: LogisticsState, rng: Random, current_day: int) -> None:
        """Scan all pending orders and attempt to create shipments for their next leg."""
        # Need to snapshot to avoid mutation issues if create_shipment affects the list
        # Though currently create_shipment only appends.
        for order in list(state.active_orders):
            if order.status == "pending" and order.current_location != order.final_destination:
                try:
                    self.create_shipment(
                        state,
                        order.current_location,
                        order.final_destination,
                        order.supplies,
                        order.units,
                        rng,
                        existing_order=order,
                        current_day=current_day
                    )
                except ValueError as e:
                    # Likely capacity or no ships; it stays 'pending' at the current hub
                    # We don't log this to the main log yet to avoid spamming
                    pass

    def create_shipment(
        self,
        state: LogisticsState,
        origin: LocationId,
        final_destination: LocationId,
        supplies: Supplies,
        units: UnitStock | None,
        rng: Random,
        existing_order: TransportOrder | None = None,
        current_day: int = 0
    ) -> None:
        """Create a movement instruction (Ship Launch or Ground Convoy).
        
        CRITICAL FIX: Stock is only deducted AFTER transport is successfully initiated.
        This prevents supplies from disappearing when no ship is available.
        """
        if units is None:
            units = UnitStock(0, 0, 0)
            
        # 1. Determine Full Path and Next Hop
        full_path = self._find_path(state, origin, final_destination)
        if not full_path or len(full_path) < 2:
            raise ValueError(f"No route found from {origin} to {final_destination}")
            
        next_hop = full_path[1]
        
        # 2. Check stock availability BEFORE attempting dispatch
        stock = state.depot_stocks[origin]
        stock_u = state.depot_units[origin]
        
        if (stock.ammo < supplies.ammo or 
            stock.fuel < supplies.fuel or 
            stock.med_spares < supplies.med_spares):
            raise ValueError(f"Insufficient supplies at {origin}")

        # 3. Determine if this is a space leg or ground leg
        is_space_leg = (
            origin == LocationId.NEW_SYSTEM_CORE or 
            origin == LocationId.DEEP_SPACE or 
            next_hop == LocationId.DEEP_SPACE or
            next_hop == LocationId.NEW_SYSTEM_CORE
        )
        
        # 4. For space legs, verify ship availability BEFORE deducting stock
        if is_space_leg:
            ship = self._find_available_ship(state, origin, supplies, units)
            if not ship:
                raise ValueError(f"No idle cargo ship available at {origin}")
        
        # 5. Now we know dispatch will succeed - create/update order
        if existing_order:
            order = existing_order
        else:
            order = TransportOrder(
                order_id=f"ORD-{rng.randint(1000,9999)}",
                origin=origin,
                final_destination=final_destination,
                supplies=supplies,
                units=units,
                current_location=origin,
                status="pending"
            )
            state.active_orders.append(order)

        # 6. Deduct from Hub Stock (only after dispatch is guaranteed)
        state.depot_stocks[origin] = Supplies(
            ammo=stock.ammo - supplies.ammo,
            fuel=stock.fuel - supplies.fuel,
            med_spares=stock.med_spares - supplies.med_spares
        )
        state.depot_units[origin] = UnitStock(
            infantry=max(0, stock_u.infantry - units.infantry),
            walkers=max(0, stock_u.walkers - units.walkers),
            support=max(0, stock_u.support - units.support)
        )

        # 7. Execute Transport
        if is_space_leg:
            # Ship was already validated above
            self._launch_cargo_ship(state, origin, next_hop, order, ship, current_day)
        else:
            # Ground convoy - create single-leg convoy with proper travel time
            route = self._find_route(state, origin, next_hop)
            travel_days = route.travel_days if route else 1
            self._create_ground_convoy(state, origin, next_hop, order, travel_days, current_day)
    
    def _find_available_ship(
        self,
        state: LogisticsState,
        origin: LocationId,
        supplies: Supplies,
        units: UnitStock
    ) -> CargoShip | None:
        """Find an idle ship at origin with sufficient capacity."""
        for ship in state.ships.values():
            if ship.location == origin and ship.state == ShipState.IDLE:
                if ship.can_load(supplies, units):
                    return ship
        return None

    def _launch_cargo_ship(
        self,
        state: LogisticsState,
        origin: LocationId,
        destination: LocationId,
        order: TransportOrder,
        ship: CargoShip,
        current_day: int = 0
    ) -> None:
        """Load a pre-validated ship and launch it."""
        # Get route for travel time
        route = self._find_route(state, origin, destination)
        if not route:
            raise ValueError("No direct route defined for space leg.")
             
        # Load order onto ship
        ship.orders.append(order)
        order.status = "transit"
        order.in_transit_leg = (origin, destination)
        order.carrier_id = f"SHIP-{ship.ship_id}"
        
        # Launch ship
        ship.destination = destination
        ship.state = ShipState.TRANSIT
        ship.days_remaining = route.travel_days
        ship.total_days = route.travel_days
        
        # Log departure
        origin_name = origin.value.upper().replace("_", " ")
        dest_name = destination.value.upper().replace("_", " ")
        self._log_event(state, current_day, f"{ship.name} departed {origin_name} → {dest_name}", "departed")

    def _create_ground_convoy(
        self,
        state: LogisticsState,
        origin: LocationId,
        destination: LocationId,
        order: TransportOrder,
        travel_days: int,
        current_day: int = 0
    ) -> None:
        """Create a single-leg ground shipment with proper travel time."""
        shipment_id = state.next_shipment_id
        shipment = Shipment(
            shipment_id=shipment_id,
            path=(origin, destination),  # Single leg only
            leg_index=0,
            orders=[order],
            days_remaining=travel_days,
            total_days=travel_days
        )
        order.status = "transit"
        order.in_transit_leg = (origin, destination)
        order.carrier_id = f"CONVOY-{shipment_id}"
        state.next_shipment_id += 1
        state.shipments.append(shipment)
        
        # Log departure
        origin_name = origin.value.replace("contested_", "").upper()
        dest_name = destination.value.replace("contested_", "").upper()
        self._log_event(state, current_day, f"Convoy #{shipment_id} departed {origin_name} → {dest_name}", "departed")

    def _find_route(self, state: LogisticsState, origin: LocationId, destination: LocationId) -> Route | None:
        for route in state.routes:
            if route.origin == origin and route.destination == destination:
                return route
        return None

    def _find_path(self, state: LogisticsState, origin: LocationId, destination: LocationId) -> tuple[LocationId, ...] | None:
        """Find path BFS."""
        if origin == destination:
            return (origin,)
        
        adjacency = {node: [] for node in LocationId}
        for route in state.routes:
            adjacency[route.origin].append(route.destination)
            
        queue = deque([origin])
        visited = {origin}
        parent = {}
        
        while queue:
            node = queue.popleft()
            for nxt in adjacency[node]:
                if nxt in visited: continue
                visited.add(nxt)
                parent[nxt] = node
                if nxt == destination:
                    queue.clear(); break
                queue.append(nxt)
                
        if destination not in parent:
            return None
            
        path = [destination]
        while path[-1] != origin:
            path.append(parent[path[-1]])
        path.reverse()
        return tuple(path)

