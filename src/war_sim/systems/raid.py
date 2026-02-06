from __future__ import annotations

from war_sim.domain.ops_models import OperationIntent, OperationTarget, OperationTypeId
from war_sim.sim.state import GameState
from war_sim.systems.operations import start_operation_phased


class RaidDeprecatedError(RuntimeError):
    pass


def start_raid(state: GameState, target: OperationTarget, rng) -> None:
    """Compatibility wrapper: raids now run through operation flow."""
    intent = OperationIntent(target=target, op_type=OperationTypeId.RAID)
    start_operation_phased(state, intent, rng)


def advance_raid_tick(state: GameState):
    raise RaidDeprecatedError("Direct raid tick control was removed; use advance_day for opType=raid")


def resolve_active_raid(state: GameState):
    raise RaidDeprecatedError("Direct raid resolve was removed; use phase decisions + advance_day")


def raid(state: GameState, target: OperationTarget, rng):
    raise RaidDeprecatedError("Direct raid API removed; start an operation with opType=raid")
