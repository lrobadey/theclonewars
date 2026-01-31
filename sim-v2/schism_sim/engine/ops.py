from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Union

from schism_sim.engine.logging import Event
from schism_sim.engine.types import Supplies


class OperationTarget(str, Enum):
    FOUNDRY = "Droid Foundry"
    COMMS = "Communications Array"
    POWER = "Power Plant"


class OperationTypeId(str, Enum):
    RAID = "raid"
    CAMPAIGN = "campaign"
    SIEGE = "siege"


class OperationPhase(str, Enum):
    CONTACT_SHAPING = "contact_shaping"
    ENGAGEMENT = "engagement"
    EXPLOIT_CONSOLIDATE = "exploit_consolidate"
    COMPLETE = "complete"


@dataclass(frozen=True)
class OperationIntent:
    """Fixed operation parameters set at start (target + type)."""

    target: OperationTarget
    op_type: OperationTypeId


@dataclass(frozen=True)
class Phase1Decisions:
    """Contact & Shaping phase decisions."""

    approach_axis: str  # direct / flank / dispersed / stealth
    fire_support_prep: str  # conserve / preparatory


@dataclass(frozen=True)
class Phase2Decisions:
    """Main Engagement phase decisions."""

    engagement_posture: str  # shock / methodical / siege / feint
    risk_tolerance: str  # low / med / high


@dataclass(frozen=True)
class Phase3Decisions:
    """Exploit & Consolidate phase decisions."""

    exploit_vs_secure: str  # push / secure
    end_state: str  # capture / raid / destroy / withdraw


PhaseDecisions = Union[Phase1Decisions, Phase2Decisions, Phase3Decisions]


@dataclass()
class OperationDecisions:
    """Collected decisions across all phases (filled incrementally)."""

    phase1: Phase1Decisions | None = None
    phase2: Phase2Decisions | None = None
    phase3: Phase3Decisions | None = None

    def is_complete(self) -> bool:
        return self.phase1 is not None and self.phase2 is not None and self.phase3 is not None


@dataclass(frozen=True)
class PhaseSummary:
    """Summary of what happened in a phase."""

    progress_delta: float
    losses: int
    supplies_spent: Supplies
    readiness_delta: float = 0.0
    cohesion_delta: float = 0.0


@dataclass(frozen=True)
class OperationPhaseRecord:
    """Complete record of a resolved phase (for AAR timeline)."""

    phase: OperationPhase
    start_day: int
    end_day: int
    decisions: PhaseDecisions
    summary: PhaseSummary
    events: list[Event]


@dataclass()
class ActiveOperation:
    """Active operation with phase-by-phase state machine."""

    intent: OperationIntent

    estimated_total_days: int
    phase_durations: dict[OperationPhase, int]

    current_phase: OperationPhase = OperationPhase.CONTACT_SHAPING
    day_in_operation: int = 0
    day_in_phase: int = 0
    phase_start_day: int = 1

    decisions: OperationDecisions = field(default_factory=OperationDecisions)

    phase_history: list[OperationPhaseRecord] = field(default_factory=list)
    pending_phase_record: OperationPhaseRecord | None = None
    awaiting_player_decision: bool = True
    auto_advance: bool = False

    sampled_enemy_strength: float | None = None
    accumulated_progress: float = 0.0
    accumulated_losses: int = 0

    @property
    def target(self) -> OperationTarget:
        return self.intent.target

    @property
    def op_type(self) -> OperationTypeId:
        return self.intent.op_type

    @property
    def estimated_days(self) -> int:
        """Backward compatibility alias for estimated_total_days."""
        return self.estimated_total_days

    def current_phase_duration(self) -> int:
        return self.phase_durations.get(self.current_phase, 1)

    def is_phase_complete(self) -> bool:
        return self.day_in_phase >= self.current_phase_duration()

    def advance_phase(self) -> None:
        """Move to the next phase."""
        phase_order = [
            OperationPhase.CONTACT_SHAPING,
            OperationPhase.ENGAGEMENT,
            OperationPhase.EXPLOIT_CONSOLIDATE,
            OperationPhase.COMPLETE,
        ]
        idx = phase_order.index(self.current_phase)
        if idx < len(phase_order) - 1:
            self.current_phase = phase_order[idx + 1]
            self.day_in_phase = 0
            self.awaiting_player_decision = self.current_phase != OperationPhase.COMPLETE


@dataclass(frozen=True)
class OperationPlan:
    """Legacy plan structure - kept for backward compatibility."""

    target: OperationTarget
    approach_axis: str
    fire_support_prep: str
    engagement_posture: str
    risk_tolerance: str
    exploit_vs_secure: str
    end_state: str
    op_type: OperationTypeId = OperationTypeId.CAMPAIGN

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
            op_type=OperationTypeId.CAMPAIGN,
        )

    def to_intent(self) -> OperationIntent:
        return OperationIntent(target=self.target, op_type=self.op_type)

    def to_phase1(self) -> Phase1Decisions:
        return Phase1Decisions(
            approach_axis=self.approach_axis,
            fire_support_prep=self.fire_support_prep,
        )

    def to_phase2(self) -> Phase2Decisions:
        return Phase2Decisions(
            engagement_posture=self.engagement_posture,
            risk_tolerance=self.risk_tolerance,
        )

    def to_phase3(self) -> Phase3Decisions:
        return Phase3Decisions(
            exploit_vs_secure=self.exploit_vs_secure,
            end_state=self.end_state,
        )

