"""Logistics system: depots, routes, and shipments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from clone_wars.engine.types import Supplies, UnitStock


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
