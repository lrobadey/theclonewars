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
            # Arrival
            arrived_at = ship.destination
            ship.location = ship.destination
            ship.state = ShipState.IDLE
            ship.destination = None
            ship.days_remaining = 0
            
            # Special Logic: Deep Space Waypoint
            # If we are at Deep Space and have orders for Spaceport, continue immediately.
            # This simulates a long journey that is split into legs for interdiction checks.
            if ship.location == LocationId.DEEP_SPACE:
                 # Check if we have cargo destined for further
                 # Ideally check path, but for MVP: Deep -> Spaceport is the only valid forward path
                 has_cargo = len(ship.orders) > 0
                 if has_cargo:
                     ship.destination = LocationId.CONTESTED_SPACEPORT
                     ship.state = ShipState.TRANSIT
                     ship.days_remaining = 1 # Lookup route ideally, but 1 day is standard
                     ship.total_days = 1
                     self._log_event(state, current_day, f"{ship.name} waypoint at DEEP SPACE", "waypoint")
                     return

            # Log arrival
            loc_name = arrived_at.value.upper().replace("_", " ") if arrived_at else "UNKNOWN"
            self._log_event(state, current_day, f"{ship.name} arrived at {loc_name}", "arrived")

            # Unload ship and process orders
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
                    current_leg_dest = shipment.destination
                    
                    if shipment.leg_index >= len(shipment.path) - 2:
                        # Final Delivery
                        self._arrive_at_location(state, current_leg_dest, shipment.orders, rng)
                        # Do not add to active_list (it is done)
                        continue 
                    else:
                        # Next Leg
                        shipment.leg_index += 1
                        shipment.days_remaining = 1 
                        active_list.append(shipment)
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
        """Process arrival of goods at a node."""
        stock = state.depot_stocks[location]
        units_stock = state.depot_units[location]

        for order in orders:
            order.current_location = location
            
            if location == order.final_destination:
                # Order Complete: Add to Stockpile
                order.status = "complete"
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
                # Refresh local references as we iterate
                stock = state.depot_stocks[location]
                units_stock = state.depot_units[location]
            else:
                # Intermediate Stop: Route to next leg
                try:
                    self.create_shipment(
                        state, 
                        location, 
                        order.final_destination, 
                        order.supplies, 
                        order.units, 
                        rng,
                        existing_order=order
                    )
                except ValueError:
                    # If we can't ship (e.g. no ship available), dump goods here for now
                    # In future: Queue for later
                    print(f"Logistics Warning: Stranded cargo at {location} destined for {order.final_destination}")
                    state.depot_stocks[location] = Supplies(
                        ammo=stock.ammo + order.supplies.ammo,
                        fuel=stock.fuel + order.supplies.fuel,
                        med_spares=stock.med_spares + order.supplies.med_spares,
                    )
                    stock = state.depot_stocks[location]

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
        """Create a movement instruction (Ship Launch or Ground Convoy)."""
        if units is None:
            units = UnitStock(0, 0, 0)
            
        # 1. Determine Full Path
        full_path = self._find_path(state, origin, final_destination)
        if not full_path or len(full_path) < 2:
            raise ValueError(f"No route found from {origin} to {final_destination}")
            
        next_hop = full_path[1]
        
        # 2. Wrap in Order if new
        if existing_order:
            order = existing_order
        else:
            # Deduct from Origin Stock if this is a NEW order
            stock = state.depot_stocks[origin]
            stock_u = state.depot_units[origin]
            
            if (stock.ammo < supplies.ammo or 
                stock.fuel < supplies.fuel or 
                stock.med_spares < supplies.med_spares):
                raise ValueError("Insufficient supplies.")
                
            # Check unit stock? (Simulated for MVP, assuming checks done by caller or infinite)
            
            state.depot_stocks[origin] = Supplies(
                ammo=stock.ammo - supplies.ammo,
                fuel=stock.fuel - supplies.fuel,
                med_spares=stock.med_spares - supplies.med_spares
            )
            # Deduct units logic here if we tracked unit source meticulously
            
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

        # 3. Execute Transport logic for Next Hop
        # Space Route?
        is_space_leg = (
            origin == LocationId.NEW_SYSTEM_CORE or 
            origin == LocationId.DEEP_SPACE or 
            next_hop == LocationId.DEEP_SPACE or
            next_hop == LocationId.NEW_SYSTEM_CORE
        )
        
        if is_space_leg:
            self._launch_cargo_ship(state, origin, next_hop, order, current_day)
        else:
            # Ground Route
            # For ground convoys, we can just assign the whole remaining path
            # assuming it's contiguous ground
            self._create_ground_convoy(state, origin, final_destination, full_path, order)

    def _launch_cargo_ship(
        self,
        state: LogisticsState,
        origin: LocationId,
        destination: LocationId,
        order: TransportOrder,
        current_day: int = 0
    ) -> None:
        """Find an idle ship at origin, load it, and launch it."""
        # 1. Find Ship
        ship = next((s for s in state.ships.values() if s.location == origin and s.state == ShipState.IDLE), None)
        if not ship:
            raise ValueError("No idle Cargo Ships available at this location.")
            
        # 2. Check Capacity
        if not ship.can_load(order.supplies, order.units):
            raise ValueError("Cargo exceeds ship capacity.")
            
        # 3. Load
        ship.orders.append(order)
        order.status = "transit"
        
        # 4. Launch
        route = self._find_route(state, origin, destination)
        if not route:
             # Should be caught by BFS but safety check
             raise ValueError("No direct route defined for space leg.")
             
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
        origin: LocationId, # Added for debug logging
        destination: LocationId, # Added for debug logging
        full_path: tuple[LocationId, ...],
        order: TransportOrder
    ) -> None:
        """Create a ground shipment."""
        shipment = Shipment(
            shipment_id=state.next_shipment_id,
            path=full_path,
            leg_index=0,
            orders=[order],
            days_remaining=1, 
            total_days=1
        )
        order.status = "transit"
        state.next_shipment_id += 1
        state.shipments.append(shipment)

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

