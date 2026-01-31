from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from schism_sim.engine.ops import OperationIntent, OperationPlan, OperationTarget
from schism_sim.engine.state import GameState
from schism_sim.engine.types import LocationId, Supplies, UnitStock


class ActionType(Enum):
    """
    Actions that cost AP (Strategic Orders):
    - START_OPERATION: 1 AP
    - START_RAID: 1 AP
    - DISPATCH_SHIPMENT: 1 AP
    - UPGRADE_FACTORY: 1 AP
    - UPGRADE_BARRACKS: 1 AP

    Free actions (Planning):
    - Queue production/barracks jobs
    - View screens, adjust settings
    """

    START_OPERATION = auto()  # Costs 1 AP
    START_RAID = auto()  # Costs 1 AP
    DISPATCH_SHIPMENT = auto()  # Costs 1 AP
    UPGRADE_FACTORY = auto()  # Costs 1 AP
    UPGRADE_BARRACKS = auto()  # Costs 1 AP


@dataclass()
class ShipmentPayload:
    origin: LocationId
    destination: LocationId
    supplies: Supplies
    units: UnitStock


@dataclass()
class PlayerAction:
    action_type: ActionType
    payload: Any = None  # Generic payload based on action type


class ActionError(Exception):
    """Raised when an action cannot be performed."""


class ActionManager:
    def __init__(self, state: GameState):
        self.state = state

    @property
    def action_points(self) -> int:
        return self.state.action_points

    def can_perform(self, action: PlayerAction) -> bool:
        """Check if an action can be performed (has enough AP)."""
        return self.state.action_points >= 1

    def perform_action(self, action: PlayerAction) -> None:
        """Execute an action that costs AP. All actions here cost 1 AP."""
        if self.state.action_points < 1:
            raise ActionError("No action points remaining (Need 1 AP).")

        if action.action_type == ActionType.START_OPERATION:
            if isinstance(action.payload, OperationIntent):
                self.state.start_operation_phased(action.payload)
            elif isinstance(action.payload, OperationPlan):
                self.state.start_operation(action.payload)
            else:
                raise ActionError("Invalid payload for START_OPERATION")

        elif action.action_type == ActionType.START_RAID:
            if not isinstance(action.payload, OperationTarget):
                raise ActionError("Invalid payload for START_RAID")
            self.state.start_raid(action.payload)

        elif action.action_type == ActionType.DISPATCH_SHIPMENT:
            if not isinstance(action.payload, ShipmentPayload):
                raise ActionError("Invalid payload for DISPATCH_SHIPMENT")

            pl = action.payload
            try:
                self.state.logistics_service.create_shipment(
                    self.state.logistics,
                    pl.origin,
                    pl.destination,
                    pl.supplies,
                    pl.units,
                    self.state.rng,
                    current_day=self.state.day,
                )
            except ValueError as e:
                raise ActionError(str(e))

        elif action.action_type == ActionType.UPGRADE_FACTORY:
            self.state.production.add_factory()

        elif action.action_type == ActionType.UPGRADE_BARRACKS:
            self.state.barracks.add_barracks()

        else:
            raise ActionError(f"Unknown action type: {action.action_type}")

        self._deduct_ap(1)

    def _deduct_ap(self, amount: int) -> None:
        self.state.action_points = max(0, self.state.action_points - amount)

    def end_day(self) -> None:
        """Explicitly end the day, resetting AP."""
        self.state.advance_day()
        self.state.action_points = 3

