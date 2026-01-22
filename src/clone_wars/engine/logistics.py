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


class ShipState(str, Enum):
    IDLE = "idle"         # At a node, ready for orders
    LOADING = "loading"   # (Not used in MVP, instantaneous)
    TRANSIT = "transit"   # Moving between nodes
    UNLOADING = "unloading" # (Not used in MVP, instantaneous)


@dataclass()
class CargoShip:
    """A specific cargo ship with fixed capacity."""
    
    ship_id: str
    location: LocationId    # Current location (or origin if in transit)
    state: ShipState = ShipState.IDLE
    
    # Payload
    supplies: Supplies = field(default_factory=lambda: Supplies(0, 0, 0))
    units: UnitStock = field(default_factory=lambda: UnitStock(0, 0, 0))
    
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

    def can_load(self, supplies: Supplies, units: UnitStock) -> bool:
        """Check if load fits in empty slots (simple replacement for MVP)."""
        # MVP Simplification: Load replaces content or adds?
        # Let's assume adds, but checks limits.
        new_ammo = self.supplies.ammo + supplies.ammo
        new_fuel = self.supplies.fuel + supplies.fuel
        # Med/Spares usually share volume, but let's assume they share 'small cargo'
        # Or just give them a slot? User didn't specify Med capacity.
        # Let's assume Med/Spares fits in Ammo or is negligible?
        # User said "200 ammo 200 fuel 1000 infantry 5 walkers". 
        # Let's give Med 100 capacity for now.
        new_med = self.supplies.med_spares + supplies.med_spares
        
        new_inf = self.units.infantry + units.infantry
        new_walkers = self.units.walkers + units.walkers
        
        return (
            new_ammo <= self.CAPACITY_AMMO
            and new_fuel <= self.CAPACITY_FUEL
            and new_inf <= self.CAPACITY_INFANTRY
            and new_walkers <= self.CAPACITY_WALKERS
            and new_med <= 100  # Implicit limit
        )


@dataclass()
class Shipment:
    """A shipment (Legacy/Ground transport abstraction)."""

    shipment_id: int
    path: tuple[LocationId, ...]
    leg_index: int
    supplies: Supplies
    units: UnitStock
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
    def final_destination(self) -> LocationId:
        return self.path[-1]


@dataclass()
class LogisticsState:
    """Logistics network state."""

    depot_stocks: dict[LocationId, Supplies]
    depot_units: dict[LocationId, UnitStock]
    routes: list[Route]
    
    # Fleet Management
    ships: dict[str, CargoShip]
    
    # Ground/Legacy Shipments (Spaceport -> Mid -> Front)
    shipments: list[Shipment]
    next_shipment_id: int
    
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
            LocationId.DEEP_SPACE: Supplies(0, 0, 0), # Not a depot, just a node
            LocationId.CONTESTED_SPACEPORT: Supplies(ammo=0, fuel=0, med_spares=0),
            LocationId.CONTESTED_MID_DEPOT: Supplies(ammo=0, fuel=0, med_spares=0),
            LocationId.CONTESTED_FRONT: Supplies(ammo=200, fuel=150, med_spares=50), # Initial stockpiles at front
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
        )
