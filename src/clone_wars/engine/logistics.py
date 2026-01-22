"""Logistics system: depots, routes, and shipments."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from clone_wars.engine.types import LocationId, Supplies, UnitStock


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
    status: str = "pending" # pending, transit, complete


class ShipState(str, Enum):
    IDLE = "idle"         # At a node, ready for orders
    TRANSIT = "transit"   # Moving between nodes


@dataclass()
class CargoShip:
    """A specific cargo ship with fixed capacity."""
    
    ship_id: str
    location: LocationId    # Current location
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
                total.med_spares + o.supplies.med_spares
            )
        return total

    @property
    def units(self) -> UnitStock:
        total = UnitStock(0, 0, 0)
        for o in self.orders:
            total = UnitStock(
                total.infantry + o.units.infantry,
                total.walkers + o.units.walkers,
                total.support + o.units.support
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
                total.med_spares + o.supplies.med_spares
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
    def new() -> LogisticsState:
        """Create initial logistics state with default network."""
        # New Route Structure:
        # Core -> Deep Space -> Contested Spaceport (Space, requires Ship)
        # Contested Spaceport -> Mid Depot -> Front (Ground, auto/legacy)
        
        routes = [
            # Space Route (Ship required)
            Route(LocationId.NEW_SYSTEM_CORE, LocationId.DEEP_SPACE, travel_days=1, interdiction_risk=0.00),
            Route(LocationId.DEEP_SPACE, LocationId.CONTESTED_SPACEPORT, travel_days=1, interdiction_risk=0.10),
            
            # Ground Route (On Planet)
            Route(LocationId.CONTESTED_SPACEPORT, LocationId.CONTESTED_MID_DEPOT, travel_days=1, interdiction_risk=0.05),
            Route(LocationId.CONTESTED_MID_DEPOT, LocationId.CONTESTED_FRONT, travel_days=1, interdiction_risk=0.20),
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
        
        # Initialize Player Fleet: 1 Ship at Core
        fleet = {
            "1": CargoShip(ship_id="1", location=LocationId.NEW_SYSTEM_CORE)
        }
        
        return LogisticsState(
            depot_stocks=depot_stocks,
            depot_units=depot_units,
            routes=routes,
            ships=fleet,
            shipments=[],
            next_shipment_id=1,
            active_orders=[],
        )
