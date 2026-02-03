"""Reports and AAR data."""

from __future__ import annotations

from dataclasses import dataclass, field

from war_sim.domain.events import FactorEvent
from war_sim.domain.ops_models import OperationPhaseRecord, OperationTarget
from war_sim.domain.types import Supplies


@dataclass(frozen=True)
class TopFactor:
    name: str
    value: float
    delta: str
    why: str


@dataclass(frozen=True)
class RaidReport:
    outcome: str  # "VICTORY" / "DEFEAT" / "STALEMATE"
    reason: str
    target: OperationTarget
    ticks: int
    your_casualties: int
    enemy_casualties: int
    your_remaining: dict[str, int]
    enemy_remaining: dict[str, int]
    supplies_used: Supplies
    key_moments: list[str]
    tick_log: list["CombatTick"]
    top_factors: list[TopFactor] = field(default_factory=list)
    events: list[FactorEvent] = field(default_factory=list)


@dataclass(frozen=True)
class AfterActionReport:
    outcome: str
    target: OperationTarget
    operation_type: str
    days: int
    losses: int
    remaining_supplies: Supplies
    top_factors: list[TopFactor]
    phases: list[OperationPhaseRecord]
    events: list[FactorEvent]


from war_sim.systems.combat import CombatTick  # noqa: E402
