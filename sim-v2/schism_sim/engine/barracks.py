"""Barracks system: queues, jobs, and output for infantry/support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from schism_sim.engine.production import _allocate_parallel_share
from schism_sim.engine.types import LocationId

logger = logging.getLogger(__name__)


class BarracksJobType(str, Enum):
    """Types of barracks jobs."""

    INFANTRY = "infantry"
    SUPPORT = "support"


DEFAULT_BARRACKS_COSTS: dict[str, int] = {
    BarracksJobType.INFANTRY.value: 1,
    BarracksJobType.SUPPORT.value: 10,
}


@dataclass()
class BarracksJob:
    """A barracks job in the queue."""

    job_type: BarracksJobType
    quantity: int
    remaining: int
    stop_at: LocationId


@dataclass(frozen=True)
class BarracksOutput:
    """A completed barracks output."""

    job_type: BarracksJobType
    quantity: int
    stop_at: LocationId


@dataclass()
class BarracksState:
    """Barracks system state."""

    barracks: int
    slots_per_barracks: int
    max_barracks: int
    queue_policy: str
    costs: dict[str, int]
    jobs: list[BarracksJob]

    @staticmethod
    def new(
        barracks: int = 2,
        slots_per_barracks: int = 20,
        max_barracks: int = 6,
        queue_policy: str = "parallel",
        costs: dict[str, int] | None = None,
    ) -> "BarracksState":
        """Create initial barracks state."""
        return BarracksState(
            barracks=barracks,
            slots_per_barracks=slots_per_barracks,
            max_barracks=max_barracks,
            queue_policy=queue_policy,
            costs=dict(costs or DEFAULT_BARRACKS_COSTS),
            jobs=[],
        )

    @property
    def capacity(self) -> int:
        """Total barracks slots available per day."""
        return self.barracks * self.slots_per_barracks

    def can_add_barracks(self) -> bool:
        return self.barracks < self.max_barracks

    def add_barracks(self, count: int = 1) -> None:
        if count <= 0:
            raise ValueError("Barracks upgrade count must be positive")
        if self.barracks + count > self.max_barracks:
            raise ValueError("Barracks upgrade exceeds maximum")
        self.barracks += count

    def _cost_for(self, job_type: BarracksJobType) -> int:
        if not isinstance(job_type, BarracksJobType):
            raise ValueError("Invalid barracks job type")
        cost = self.costs.get(job_type.value)
        if cost is None:
            raise ValueError(f"No cost configured for job type {job_type.value}")
        if cost <= 0:
            raise ValueError(f"Invalid cost for job type {job_type.value}")
        return cost

    def queue_job(
        self,
        job_type: BarracksJobType,
        quantity: int,
        stop_at: LocationId = LocationId.NEW_SYSTEM_CORE,
    ) -> None:
        """Queue a new barracks job."""
        if quantity <= 0:
            raise ValueError("Barracks quantity must be positive")
        if self.capacity <= 0:
            logger.warning(
                "Barracks capacity is zero; queueing will stall until barracks are built."
            )

        cost = self._cost_for(job_type)
        job = BarracksJob(
            job_type=job_type,
            quantity=quantity,
            remaining=quantity * cost,
            stop_at=stop_at,
        )
        self.jobs.append(job)

    def tick(self) -> list[BarracksOutput]:
        """Advance barracks production by one day. Returns completed outputs."""
        if self.queue_policy != "parallel":
            raise ValueError(f"Unsupported barracks queue policy: {self.queue_policy}")
        if self.capacity <= 0:
            logger.warning("Barracks capacity is zero; skipping barracks tick.")
            return []

        if not self.jobs:
            return []

        work_remaining = [job.remaining for job in self.jobs]
        active_indices = [i for i, remaining in enumerate(work_remaining) if remaining > 0]
        if not active_indices:
            return self._collect_completed()

        _allocate_parallel_share(work_remaining, self.capacity, active_indices)

        for i, job in enumerate(self.jobs):
            job.remaining = max(0, work_remaining[i])

        return self._collect_completed()

    def _collect_completed(self) -> list[BarracksOutput]:
        completed: list[BarracksOutput] = []
        for i in range(len(self.jobs) - 1, -1, -1):
            job = self.jobs[i]
            if job.remaining <= 0:
                completed.append(
                    BarracksOutput(
                        job_type=job.job_type, quantity=job.quantity, stop_at=job.stop_at
                    )
                )
                self.jobs.pop(i)
        completed.reverse()
        return completed

    def get_eta_summary(self) -> list[tuple[str, int, int, str]]:
        """Get summary of jobs with ETAs. Returns list of (type, quantity, eta_days, stop_at)."""
        if self.queue_policy != "parallel":
            raise ValueError(f"Unsupported barracks queue policy: {self.queue_policy}")
        if self.capacity <= 0:
            logger.warning("Barracks capacity is zero; ETA will be unknown.")
            return []
        if not self.jobs:
            return []

        work_remaining = [job.remaining for job in self.jobs]
        completion_days = [0] * len(self.jobs)
        day = 0

        while True:
            active_indices = [i for i, remaining in enumerate(work_remaining) if remaining > 0]
            if not active_indices:
                break
            day += 1

            before = list(work_remaining)
            _allocate_parallel_share(work_remaining, self.capacity, active_indices)

            for i, remaining in enumerate(work_remaining):
                if remaining <= 0 and before[i] > 0 and completion_days[i] == 0:
                    completion_days[i] = day

        summary: list[tuple[str, int, int, str]] = []
        for i, job in enumerate(self.jobs):
            c_day = completion_days[i]
            if c_day == 0 and job.remaining > 0:
                c_day = -1
            elif c_day == 0 and job.remaining <= 0:
                c_day = 1
            summary.append((job.job_type.value, job.quantity, c_day, job.stop_at.value))

        return summary

