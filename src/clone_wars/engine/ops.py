from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OperationTarget(str, Enum):
    FOUNDRY = "Droid Foundry"
    COMMS = "Communications Array"
    POWER = "Power Plant"


@dataclass(frozen=True, slots=True)
class OperationPlan:
    target: OperationTarget
    approach_axis: str
    fire_support_prep: str
    engagement_posture: str
    risk_tolerance: str
    exploit_vs_secure: str
    end_state: str

    @staticmethod
    def quickstart(target: OperationTarget) -> "OperationPlan":
        return OperationPlan(
            target=target,
            approach_axis="direct",
            fire_support_prep="preparatory",
            engagement_posture="methodical",
            risk_tolerance="med",
            exploit_vs_secure="secure",
            end_state="capture",
        )


@dataclass(slots=True)
class ActiveOperation:
    plan: OperationPlan
    estimated_days: int
    day_in_operation: int = 0

    @property
    def target(self) -> OperationTarget:
        return self.plan.target
