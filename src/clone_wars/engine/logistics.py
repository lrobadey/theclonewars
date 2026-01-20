"""Logistics system: depots, routes, and shipments."""

from __future__ import annotations

from dataclasses import dataclass
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
class Shipment:
    """A shipment in transit."""

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
    shipments: list[Shipment]
    next_shipment_id: int

    @staticmethod
    def new() -> LogisticsState:
        """Create initial logistics state with default network."""
        # MVP Map: Core -> Deep Space A -> Contested -> Deep Space B -> Collective Core
        routes = [
            # New System Side
            Route(LocationId.NEW_SYSTEM_CORE, LocationId.DEEP_SPACE_A, travel_days=1, interdiction_risk=0.05),
            Route(LocationId.DEEP_SPACE_A, LocationId.CONTESTED_WORLD, travel_days=1, interdiction_risk=0.10),
            
            # Collective Side
            Route(LocationId.COLLECTIVE_CORE, LocationId.DEEP_SPACE_B, travel_days=1, interdiction_risk=0.05),
            Route(LocationId.DEEP_SPACE_B, LocationId.CONTESTED_WORLD, travel_days=1, interdiction_risk=0.10),
        ]
        
        depot_stocks = {
            LocationId.NEW_SYSTEM_CORE: Supplies(ammo=500, fuel=400, med_spares=200),
            LocationId.DEEP_SPACE_A: Supplies(ammo=0, fuel=0, med_spares=0),
            LocationId.CONTESTED_WORLD: Supplies(ammo=100, fuel=80, med_spares=40),
            LocationId.DEEP_SPACE_B: Supplies(ammo=0, fuel=0, med_spares=0),
            LocationId.COLLECTIVE_CORE: Supplies(ammo=500, fuel=400, med_spares=200),
        }
        
        depot_units = {
            LocationId.NEW_SYSTEM_CORE: UnitStock(infantry=200, walkers=5, support=4),
            LocationId.DEEP_SPACE_A: UnitStock(0, 0, 0),
            LocationId.CONTESTED_WORLD: UnitStock(infantry=100, walkers=2, support=1),
            LocationId.DEEP_SPACE_B: UnitStock(0, 0, 0),
            LocationId.COLLECTIVE_CORE: UnitStock(infantry=200, walkers=5, support=4),
        }
        
        return LogisticsState(
            depot_stocks=depot_stocks,
            depot_units=depot_units,
            routes=routes,
            shipments=[],
            next_shipment_id=1,
        )
