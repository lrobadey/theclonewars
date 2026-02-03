"""Logistics system: depots, routes, and shipments."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from random import Random

from war_sim.domain.types import LocationId, PlanetState, Supplies, UnitStock


@dataclass()
class Route:
    """A route between two location nodes."""

    origin: LocationId
    destination: LocationId
    travel_days: int
    interdiction_risk: float  # 0.0 to 1.0


@dataclass()
class TransportOrder:
    """A high-level order to move goods from A to B."""

    order_id: str
    origin: LocationId
    final_destination: LocationId
    supplies: Supplies
    units: UnitStock
    # Tracking
    current_location: LocationId
    status: str = "pending"  # pending, transit, complete
    # Transit tracking for UI: (origin, destination) of current leg, or None if not in transit
    in_transit_leg: tuple[LocationId, LocationId] | None = None
    # Carrier ID (ship_id or shipment_id) for tracking
    carrier_id: str | None = None


class ShipState(str, Enum):
    IDLE = "idle"  # At a node, ready for orders
    TRANSIT = "transit"  # Moving between nodes


@dataclass()
class CargoShip:
    """A specific cargo ship with fixed capacity."""

    ship_id: str
    location: LocationId  # Current location
    state: ShipState = ShipState.IDLE

    # Payload now tracks which orders are on board
    orders: list[TransportOrder] = field(default_factory=list)

    # Transit info (if state == TRANSIT)
    destination: LocationId | None = None
    days_remaining: int = 0
    total_days: int = 0
    interdicted: bool = False

    # Capacity Constants (Static for MVP)
    CAPACITY_AMMO: int = 200
    CAPACITY_FUEL: int = 200
    CAPACITY_INFANTRY: int = 1000
    CAPACITY_WALKERS: int = 5

    @property
    def name(self) -> str:
        return f"Ship {self.ship_id}"

    @property
    def supplies(self) -> Supplies:
        total = Supplies(0, 0, 0)
        for o in self.orders:
            total = Supplies(
                total.ammo + o.supplies.ammo,
                total.fuel + o.supplies.fuel,
                total.med_spares + o.supplies.med_spares,
            )
        return total

    @property
    def units(self) -> UnitStock:
        total = UnitStock(0, 0, 0)
        for o in self.orders:
            total = UnitStock(
                total.infantry + o.units.infantry,
                total.walkers + o.units.walkers,
                total.support + o.units.support,
            )
        return total

    def can_load(self, supplies: Supplies, units: UnitStock) -> bool:
        """Check if load fits in empty slots."""
        current_supplies = self.supplies
        current_units = self.units

        new_ammo = current_supplies.ammo + supplies.ammo
        new_fuel = current_supplies.fuel + supplies.fuel
        new_med = current_supplies.med_spares + supplies.med_spares

        new_inf = current_units.infantry + units.infantry
        new_walkers = current_units.walkers + units.walkers

        return (
            new_ammo <= self.CAPACITY_AMMO
            and new_fuel <= self.CAPACITY_FUEL
            and new_inf <= self.CAPACITY_INFANTRY
            and new_walkers <= self.CAPACITY_WALKERS
            and new_med <= 100
        )


@dataclass()
class Shipment:
    """A shipment (Legacy/Ground transport abstraction)."""

    shipment_id: int
    # Path is now just the physical route taken by this specific convoy
    path: tuple[LocationId, ...]
    leg_index: int

    # Payload
    orders: list[TransportOrder]

    days_remaining: int
    total_days: int
    interdicted: bool = False
    # If interdicted, percent of cargo lost on this leg (0.0-1.0). Used for UI clarity.
    interdiction_loss_pct: float = 0.0

    @property
    def origin(self) -> LocationId:
        return self.path[self.leg_index]

    @property
    def destination(self) -> LocationId:
        return self.path[self.leg_index + 1]

    @property
    def supplies(self) -> Supplies:
        total = Supplies(0, 0, 0)
        for o in self.orders:
            total = Supplies(
                total.ammo + o.supplies.ammo,
                total.fuel + o.supplies.fuel,
                total.med_spares + o.supplies.med_spares,
            )
        return total

    @property
    def units(self) -> UnitStock:
        total = UnitStock(0, 0, 0)
        for o in self.orders:
            total = UnitStock(
                total.infantry + o.units.infantry,
                total.walkers + o.units.walkers,
                total.support + o.units.support,
            )
        return total


@dataclass(frozen=True)
class TransitLogEntry:
    """A log entry for transit events."""

    day: int
    message: str
    event_type: str  # "departed", "arrived", "interdicted", "loaded"


@dataclass()
class LogisticsState:
    """Logistics network state."""

    depot_stocks: dict[LocationId, Supplies]
    depot_units: dict[LocationId, UnitStock]
    routes: list[Route]

    # Fleet Management
    ships: dict[str, CargoShip]

    # Ground/Legacy Shipments
    shipments: list[Shipment]
    next_shipment_id: int

    # All active orders in the system (waiting or moving)
    active_orders: list[TransportOrder] = field(default_factory=list)

    # Transit activity log (most recent first)
    transit_log: list[TransitLogEntry] = field(default_factory=list)

    @staticmethod
    def new() -> "LogisticsState":
        """Create initial logistics state with default network."""
        routes = [
            Route(
                LocationId.NEW_SYSTEM_CORE,
                LocationId.DEEP_SPACE,
                travel_days=1,
                interdiction_risk=0.00,
            ),
            Route(
                LocationId.DEEP_SPACE,
                LocationId.CONTESTED_SPACEPORT,
                travel_days=1,
                interdiction_risk=0.10,
            ),
            Route(
                LocationId.CONTESTED_SPACEPORT,
                LocationId.CONTESTED_MID_DEPOT,
                travel_days=1,
                interdiction_risk=0.05,
            ),
            Route(
                LocationId.CONTESTED_MID_DEPOT,
                LocationId.CONTESTED_FRONT,
                travel_days=1,
                interdiction_risk=0.20,
            ),
        ]

        depot_stocks = {
            LocationId.NEW_SYSTEM_CORE: Supplies(ammo=1000, fuel=1000, med_spares=400),
            LocationId.DEEP_SPACE: Supplies(0, 0, 0),
            LocationId.CONTESTED_SPACEPORT: Supplies(ammo=0, fuel=0, med_spares=0),
            LocationId.CONTESTED_MID_DEPOT: Supplies(ammo=0, fuel=0, med_spares=0),
            LocationId.CONTESTED_FRONT: Supplies(ammo=200, fuel=150, med_spares=50),
        }

        depot_units = {
            LocationId.NEW_SYSTEM_CORE: UnitStock(infantry=1000, walkers=10, support=10),
            LocationId.DEEP_SPACE: UnitStock(0, 0, 0),
            LocationId.CONTESTED_SPACEPORT: UnitStock(0, 0, 0),
            LocationId.CONTESTED_MID_DEPOT: UnitStock(0, 0, 0),
            LocationId.CONTESTED_FRONT: UnitStock(0, 0, 0),
        }

        fleet = {"1": CargoShip(ship_id="1", location=LocationId.NEW_SYSTEM_CORE)}

        return LogisticsState(
            depot_stocks=depot_stocks,
            depot_units=depot_units,
            routes=routes,
            ships=fleet,
            shipments=[],
            next_shipment_id=1,
            active_orders=[],
        )


class LogisticsService:
    """Service for handling logistics operations."""

    def tick(
        self, state: LogisticsState, planet: PlanetState, rng: Random, current_day: int = 0
    ) -> None:
        """Advance logistics by one day: move ships and ground convoys."""

        existing_shipments = list(state.shipments)

        for ship in state.ships.values():
            self._tick_ship(ship, state, planet, rng, current_day)

        self._tick_ground_convoys(state, planet, rng, existing_shipments, current_day)

        self._dispatch_pending_orders(state, rng, current_day)

    def _log_event(self, state: LogisticsState, day: int, message: str, event_type: str) -> None:
        entry = TransitLogEntry(day=day, message=message, event_type=event_type)
        state.transit_log.insert(0, entry)
        if len(state.transit_log) > 20:
            state.transit_log = state.transit_log[:20]

    def _tick_ship(
        self,
        ship: CargoShip,
        state: LogisticsState,
        planet: PlanetState,
        rng: Random,
        current_day: int = 0,
    ) -> None:
        if ship.state != ShipState.TRANSIT:
            return

        ship.days_remaining -= 1
        if ship.days_remaining <= 0:
            arrived_at = ship.destination
            ship.location = ship.destination
            ship.state = ShipState.IDLE
            ship.destination = None
            ship.days_remaining = 0

            loc_name = arrived_at.value.upper().replace("_", " ") if arrived_at else "UNKNOWN"
            self._log_event(state, current_day, f"{ship.name} arrived at {loc_name}", "arrived")

            self._arrive_at_location(state, ship.location, ship.orders, rng, current_day)

            ship.orders = []

    def _tick_ground_convoys(
        self,
        state: LogisticsState,
        planet: PlanetState,
        rng: Random,
        current_shipments: list[Shipment],
        current_day: int,
    ) -> None:
        ids_to_tick = {s.shipment_id for s in current_shipments}
        active_list: list[Shipment] = []

        for shipment in state.shipments:
            if shipment.shipment_id in ids_to_tick:
                self._maybe_interdict_ground_convoy(state, shipment, rng, current_day)
                shipment.days_remaining -= 1
                if shipment.days_remaining <= 0:
                    self._arrive_at_location(state, shipment.destination, shipment.orders, rng, current_day)
                else:
                    active_list.append(shipment)
            else:
                active_list.append(shipment)

        state.shipments = active_list

    def _maybe_interdict_ground_convoy(
        self,
        state: LogisticsState,
        shipment: Shipment,
        rng: Random,
        current_day: int,
    ) -> None:
        if shipment.interdicted:
            return

        route = self._find_route(state, shipment.origin, shipment.destination)
        if not route or route.interdiction_risk <= 0.0:
            return

        if rng.random() >= route.interdiction_risk:
            return

        loss_pct = rng.uniform(0.1, 0.4)

        for order in shipment.orders:
            old_supplies = order.supplies
            old_units = order.units

            order.supplies = Supplies(
                ammo=int(old_supplies.ammo * (1 - loss_pct)),
                fuel=int(old_supplies.fuel * (1 - loss_pct)),
                med_spares=int(old_supplies.med_spares * (1 - loss_pct)),
            )
            order.units = UnitStock(
                infantry=int(old_units.infantry * (1 - loss_pct)),
                walkers=int(old_units.walkers * (1 - loss_pct)),
                support=int(old_units.support * (1 - loss_pct)),
            )

        shipment.interdicted = True
        shipment.interdiction_loss_pct = loss_pct

        self._log_event(
            state,
            current_day,
            f"Convoy {shipment.shipment_id} interdicted on {shipment.origin.value} -> {shipment.destination.value}",
            "interdicted",
        )

    def _arrive_at_location(
        self,
        state: LogisticsState,
        location: LocationId,
        orders: list[TransportOrder],
        rng: Random,
        current_day: int,
    ) -> None:
        completed_ids: set[str] = set()
        for order in orders:
            order.current_location = location

            stock = state.depot_stocks[location]
            units_stock = state.depot_units[location]
            state.depot_stocks[location] = Supplies(
                ammo=stock.ammo + order.supplies.ammo,
                fuel=stock.fuel + order.supplies.fuel,
                med_spares=stock.med_spares + order.supplies.med_spares,
            )
            state.depot_units[location] = UnitStock(
                infantry=units_stock.infantry + order.units.infantry,
                walkers=units_stock.walkers + order.units.walkers,
                support=units_stock.support + order.units.support,
            )

            if location == order.final_destination:
                order.status = "complete"
                completed_ids.add(order.order_id)
                dest_name = (
                    location.value.replace("contested_", "")
                    .replace("new_system_", "")
                    .replace("_", " ")
                    .strip()
                    .upper()
                )
                summary_parts: list[str] = []
                if order.supplies.ammo:
                    summary_parts.append(f"A-{order.supplies.ammo}")
                if order.supplies.fuel:
                    summary_parts.append(f"F-{order.supplies.fuel}")
                if order.supplies.med_spares:
                    summary_parts.append(f"M-{order.supplies.med_spares}")
                if order.units.infantry:
                    summary_parts.append(f"I-{order.units.infantry}")
                if order.units.walkers:
                    summary_parts.append(f"W-{order.units.walkers}")
                if order.units.support:
                    summary_parts.append(f"S-{order.units.support}")
                summary = f" ({' '.join(summary_parts)})" if summary_parts else ""
                self._log_event(
                    state,
                    current_day,
                    f"Order {order.order_id} completed at {dest_name}{summary}",
                    "completed",
                )
            else:
                order.status = "pending"

            stock = state.depot_stocks[location]
            units_stock = state.depot_units[location]

        if completed_ids:
            state.active_orders = [order for order in state.active_orders if order.order_id not in completed_ids]

    def _dispatch_pending_orders(self, state: LogisticsState, rng: Random, current_day: int) -> None:
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
                        current_day=current_day,
                    )
                except ValueError:
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
        current_day: int = 0,
    ) -> None:
        if units is None:
            units = UnitStock(0, 0, 0)

        full_path = self._find_path(state, origin, final_destination)
        if not full_path or len(full_path) < 2:
            raise ValueError(f"No route found from {origin} to {final_destination}")

        next_hop = full_path[1]

        stock = state.depot_stocks[origin]
        stock_u = state.depot_units[origin]

        if (
            stock.ammo < supplies.ammo
            or stock.fuel < supplies.fuel
            or stock.med_spares < supplies.med_spares
        ):
            raise ValueError(f"Insufficient supplies at {origin}")
        if (
            stock_u.infantry < units.infantry
            or stock_u.walkers < units.walkers
            or stock_u.support < units.support
        ):
            raise ValueError(f"Insufficient units at {origin}")

        is_space_leg = (
            origin == LocationId.NEW_SYSTEM_CORE
            or origin == LocationId.DEEP_SPACE
            or next_hop == LocationId.DEEP_SPACE
            or next_hop == LocationId.NEW_SYSTEM_CORE
        )

        if is_space_leg:
            ship = self._find_available_ship(state, origin, supplies, units)
            if not ship:
                raise ValueError(f"No idle cargo ship available at {origin}")

        if existing_order:
            order = existing_order
        else:
            order = TransportOrder(
                order_id=str(len(state.active_orders) + 1),
                origin=origin,
                final_destination=final_destination,
                supplies=supplies,
                units=units,
                current_location=origin,
                status="pending",
            )
            state.active_orders.append(order)

        state.depot_stocks[origin] = Supplies(
            ammo=stock.ammo - supplies.ammo,
            fuel=stock.fuel - supplies.fuel,
            med_spares=stock.med_spares - supplies.med_spares,
        )
        state.depot_units[origin] = UnitStock(
            infantry=stock_u.infantry - units.infantry,
            walkers=stock_u.walkers - units.walkers,
            support=stock_u.support - units.support,
        )

        if is_space_leg:
            self._launch_ship(order, ship, origin, next_hop, state, current_day)
        else:
            self._launch_ground_convoy(order, origin, next_hop, state, current_day)

    def _launch_ship(
        self,
        order: TransportOrder,
        ship: CargoShip,
        origin: LocationId,
        destination: LocationId,
        state: LogisticsState,
        current_day: int,
    ) -> None:
        route = self._find_route(state, origin, destination)
        if not route:
            raise ValueError("No route for ship leg")
        ship.orders.append(order)
        ship.state = ShipState.TRANSIT
        ship.destination = destination
        ship.days_remaining = route.travel_days
        ship.total_days = route.travel_days
        order.in_transit_leg = (origin, destination)
        order.status = "transit"
        order.carrier_id = ship.ship_id
        self._log_event(state, current_day, f"{ship.name} departed {origin.value}", "departed")

    def _launch_ground_convoy(
        self,
        order: TransportOrder,
        origin: LocationId,
        destination: LocationId,
        state: LogisticsState,
        current_day: int,
    ) -> None:
        route = self._find_route(state, origin, destination)
        if not route:
            raise ValueError("No route for convoy leg")
        shipment = Shipment(
            shipment_id=state.next_shipment_id,
            path=(origin, destination),
            leg_index=0,
            orders=[order],
            days_remaining=route.travel_days,
            total_days=route.travel_days,
        )
        state.next_shipment_id += 1
        state.shipments.append(shipment)
        order.in_transit_leg = (origin, destination)
        order.status = "transit"
        order.carrier_id = str(shipment.shipment_id)
        self._log_event(state, current_day, f"Convoy {shipment.shipment_id} departed {origin.value}", "departed")

    def _find_route(self, state: LogisticsState, origin: LocationId, destination: LocationId) -> Route | None:
        for r in state.routes:
            if r.origin == origin and r.destination == destination:
                return r
        return None

    def _find_path(
        self, state: LogisticsState, origin: LocationId, destination: LocationId
    ) -> tuple[LocationId, ...] | None:
        graph: dict[LocationId, list[LocationId]] = {}
        for route in state.routes:
            graph.setdefault(route.origin, []).append(route.destination)

        queue = deque([[origin]])
        visited = {origin}
        while queue:
            path = queue.popleft()
            node = path[-1]
            if node == destination:
                return tuple(path)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None

    def _find_available_ship(
        self, state: LogisticsState, origin: LocationId, supplies: Supplies, units: UnitStock
    ) -> CargoShip | None:
        for ship in state.ships.values():
            if ship.location != origin or ship.state != ShipState.IDLE:
                continue
            if ship.can_load(supplies, units):
                return ship
        return None
