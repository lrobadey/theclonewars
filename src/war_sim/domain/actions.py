"""Action definitions for reducer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias, Union

from war_sim.domain.ops_models import OperationIntent, OperationTarget
from war_sim.domain.types import LocationId, Supplies, UnitStock


@dataclass(frozen=True)
class AdvanceDay:
    pass


@dataclass(frozen=True)
class QueueProduction:
    job_type: str
    quantity: int
    stop_at: LocationId


@dataclass(frozen=True)
class QueueBarracks:
    job_type: str
    quantity: int
    stop_at: LocationId


@dataclass(frozen=True)
class UpgradeFactory:
    count: int = 1


@dataclass(frozen=True)
class UpgradeBarracks:
    count: int = 1


@dataclass(frozen=True)
class DispatchShipment:
    origin: LocationId
    destination: LocationId
    supplies: Supplies
    units: UnitStock


@dataclass(frozen=True)
class StartOperation:
    intent: OperationIntent


@dataclass(frozen=True)
class StartRaid:
    target: OperationTarget


@dataclass(frozen=True)
class SubmitPhaseDecisions:
    decisions: object


@dataclass(frozen=True)
class AcknowledgePhaseReport:
    pass


@dataclass(frozen=True)
class RaidTick:
    pass


@dataclass(frozen=True)
class RaidResolve:
    pass


@dataclass(frozen=True)
class AcknowledgeAar:
    pass


Action: TypeAlias = Union[
    AdvanceDay,
    QueueProduction,
    QueueBarracks,
    UpgradeFactory,
    UpgradeBarracks,
    DispatchShipment,
    StartOperation,
    StartRaid,
    SubmitPhaseDecisions,
    AcknowledgePhaseReport,
    RaidTick,
    RaidResolve,
    AcknowledgeAar,
]
