from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from clone_wars.engine.ops import OperationPlan
from clone_wars.engine.state import GameState


class ActionType(Enum):
    ADVANCE_TURN = auto()  # Costs 1 AP. If AP=0, day likely ends.
    WAIT = auto()  # Costs 1 AP. Recover small readiness?
    START_OPERATION = auto()  # Costs 1 AP (Initiate).
    
    # Management actions (Free or AP?)
    # For MVP, let's make management free, but "Execution" costs AP.
    # Actually, Design says "3 Command Actions per day".
    # Buying upgrades or changing production should probably cost AP in a strict strategy game.
    # BUT, forcing AP for queuing a simplistic production job might be annoying.
    # Let's stick to:
    # - Start Operation: 1 AP
    # - Upgrade Infrastructure: 1 AP
    # - Logistics Re-route (if we add it): 1 AP
    # - "Pass/Wait": 1 AP
    # - Queue Production: Free (planning).
    
    UPGRADE_FACTORY = auto()
    UPGRADE_BARRACKS = auto()


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
        if self.state.action_points <= 0:
            # Only allow ending the day if AP is 0?
            # Actually, if AP is 0, the only valid thing is "End Day" which refuels AP.
            # But "ADVANCE_TURN" here implies spending AP.
            # Let's say "End Day" is a special system event, not a 1 AP action.
            # But the button says "Next Day".
            return False
            
        return True

    def perform_action(self, action: PlayerAction) -> None:
        if self.state.action_points <= 0:
             raise ActionError("No action points remaining. End the day.")

        if action.action_type == ActionType.ADVANCE_TURN:
            # "Wait" / "Pass"
            self._deduct_ap(1)
            
        elif action.action_type == ActionType.WAIT:
            self._deduct_ap(1)
            # Recover slightly?
            self.state.task_force.readiness = min(1.0, self.state.task_force.readiness + 0.05)

        elif action.action_type == ActionType.START_OPERATION:
            if not isinstance(action.payload, OperationPlan):
                raise ActionError("Invalid payload for START_OPERATION")
            self.state.start_operation(action.payload)
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
