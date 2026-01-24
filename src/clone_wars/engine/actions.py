from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from clone_wars.engine.ops import OperationPlan
from clone_wars.engine.state import GameState


class ActionType(Enum):
    """
    Actions that cost AP (Strategic Orders):
    - START_OPERATION: 1 AP
    - DISPATCH_SHIPMENT: 1 AP
    - UPGRADE_FACTORY: 1 AP
    - UPGRADE_BARRACKS: 1 AP
    
    Free actions (Planning):
    - Queue production/barracks jobs
    - View screens, adjust settings
    """
    START_OPERATION = auto()  # Costs 1 AP
    DISPATCH_SHIPMENT = auto()  # Costs 1 AP
    UPGRADE_FACTORY = auto()  # Costs 1 AP
    UPGRADE_BARRACKS = auto()  # Costs 1 AP


@dataclass()
class PlayerAction:
    action_type: ActionType
    payload: Any = None  # Flexible payload


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
        if self.state.action_points <= 0:
            raise ActionError("No action points remaining. End the day.")

        if action.action_type == ActionType.START_OPERATION:
            if not isinstance(action.payload, OperationPlan):
                raise ActionError("Invalid payload for START_OPERATION")
            self.state.start_operation(action.payload)
            self._deduct_ap(1)

        elif action.action_type == ActionType.DISPATCH_SHIPMENT:
            self._deduct_ap(1)

        elif action.action_type == ActionType.UPGRADE_FACTORY:
            self.state.production.add_factory()
            self._deduct_ap(1)
            
        elif action.action_type == ActionType.UPGRADE_BARRACKS:
            self.state.barracks.add_barracks()
            self._deduct_ap(1)

    def _deduct_ap(self, amount: int) -> None:
        self.state.action_points = max(0, self.state.action_points - amount)

    def end_day(self) -> None:
        """Explicitly end the day, resetting AP."""
        self.state.advance_day()
        self.state.action_points = 3
