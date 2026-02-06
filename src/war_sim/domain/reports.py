"""Reports and AAR data."""

from __future__ import annotations

from dataclasses import dataclass

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
    """Deprecated compatibility model; raids are now unified operations."""

    outcome: str
    reason: str
    target: OperationTarget
    ticks: int
    your_casualties: int
    enemy_casualties: int
    your_remaining: dict[str, int]
    enemy_remaining: dict[str, int]
    supplies_used: Supplies
    key_moments: list[str]
    top_factors: list[TopFactor]
    events: list[FactorEvent]


@dataclass(frozen=True)
class AfterActionReport:
    outcome: str
    target: OperationTarget
    operation_type: str
    days: int
    losses: int
    enemy_losses: int
    remaining_supplies: Supplies
    top_factors: list[TopFactor]
    phases: list[OperationPhaseRecord]
    events: list[FactorEvent]
