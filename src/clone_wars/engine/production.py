"""Production system: queues, jobs, and output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging

from clone_wars.engine.types import LocationId

logger = logging.getLogger(__name__)


class ProductionJobType(str, Enum):
    """Types of production jobs."""

    AMMO = "ammo"
    FUEL = "fuel"
    MED_SPARES = "med_spares"
    WALKERS = "walkers"


DEFAULT_FACTORY_COSTS: dict[str, int] = {
    ProductionJobType.AMMO.value: 20,
    ProductionJobType.FUEL.value: 20,
    ProductionJobType.MED_SPARES.value: 20,
    ProductionJobType.WALKERS.value: 20,
}


@dataclass()
class ProductionJob:
    """A production job in the queue."""

    job_type: ProductionJobType
    quantity: int
    remaining: int
    stop_at: LocationId


@dataclass(frozen=True)
class ProductionOutput:
    """A completed production output."""

    job_type: ProductionJobType
    quantity: int
    stop_at: LocationId


def _allocate_parallel_share(
    work_remaining: list[int],
    capacity: int,
    active_indices: list[int],
) -> list[int]:
    """Apply deterministic fair-share allocation to active jobs.

    The policy is "parallel" fair-share: each active job receives an equal base
    share, and the first N jobs in queue order receive one extra slot if needed.
    If a job finishes early, its unused capacity is redistributed within the day.
    Returns the list of still-active indices after allocation.
    """

    capacity_remaining = capacity
    active = list(active_indices)

    while active and capacity_remaining > 0:
        count_active = len(active)
        base_share = capacity_remaining // count_active
        extra_slots = capacity_remaining % count_active
        spent_this_round = 0
        next_active: list[int] = []

        for i, idx in enumerate(active):
            allocation = base_share + (1 if i < extra_slots else 0)
            if allocation <= 0:
                next_active.append(idx)
                continue

            needed = work_remaining[idx]
            used = min(allocation, needed)
            work_remaining[idx] -= used
            spent_this_round += used

            if work_remaining[idx] > 0:
                next_active.append(idx)

        capacity_remaining -= spent_this_round
        if not next_active or capacity_remaining <= 0:
            return next_active
        if spent_this_round <= 0:
            return next_active

        active = next_active

    return active


@dataclass()
class ProductionState:
    """Production system state."""

    factories: int
    slots_per_factory: int
    max_factories: int
    queue_policy: str
    costs: dict[str, int]
    jobs: list[ProductionJob]

    @staticmethod
    def new(
        factories: int = 3,
        slots_per_factory: int = 20,
        max_factories: int = 6,
        queue_policy: str = "parallel",
        costs: dict[str, int] | None = None,
    ) -> ProductionState:
        """Create initial production state."""
        return ProductionState(
            factories=factories,
            slots_per_factory=slots_per_factory,
            max_factories=max_factories,
            queue_policy=queue_policy,
            costs=dict(costs or DEFAULT_FACTORY_COSTS),
            jobs=[],
        )

    @property
    def capacity(self) -> int:
        """Total production slots available per day."""
        return self.factories * self.slots_per_factory

    def can_add_factory(self) -> bool:
        return self.factories < self.max_factories

    def add_factory(self, count: int = 1) -> None:
        if count <= 0:
            raise ValueError("Factory upgrade count must be positive")
        if self.factories + count > self.max_factories:
            raise ValueError("Factory upgrade exceeds maximum")
        self.factories += count

    def _cost_for(self, job_type: ProductionJobType) -> int:
        if not isinstance(job_type, ProductionJobType):
            raise ValueError("Invalid production job type")
        cost = self.costs.get(job_type.value)
        if cost is None:
            raise ValueError(f"No cost configured for job type {job_type.value}")
        if cost <= 0:
            raise ValueError(f"Invalid cost for job type {job_type.value}")
        return cost

    def queue_job(
        self, job_type: ProductionJobType, quantity: int, stop_at: LocationId = LocationId.NEW_SYSTEM_CORE
    ) -> None:
        """Queue a new production job."""
        if quantity <= 0:
            raise ValueError("Production quantity must be positive")
        if self.capacity <= 0:
            logger.warning("Production capacity is zero; queueing will stall until factories are built.")

        cost = self._cost_for(job_type)
        job = ProductionJob(
            job_type=job_type,
            quantity=quantity,
            remaining=quantity * cost,
            stop_at=stop_at,
        )
        self.jobs.append(job)

    def tick(self) -> list[ProductionOutput]:
        """Advance production by one day. Returns completed outputs."""
        if self.queue_policy != "parallel":
            raise ValueError(f"Unsupported production queue policy: {self.queue_policy}")
        if self.capacity <= 0:
            logger.warning("Production capacity is zero; skipping production tick.")
            return []

        if not self.jobs:
            return []

        work_remaining = [job.remaining for job in self.jobs]
        active_indices = [i for i, remaining in enumerate(work_remaining) if remaining > 0]
        if not active_indices:
            return self._collect_completed()

        # Deterministic fair-share allocation (parallel policy).
        _allocate_parallel_share(work_remaining, self.capacity, active_indices)

        for i, job in enumerate(self.jobs):
            job.remaining = max(0, work_remaining[i])

        return self._collect_completed()

    def _collect_completed(self) -> list[ProductionOutput]:
        completed: list[ProductionOutput] = []
        for i in range(len(self.jobs) - 1, -1, -1):
            job = self.jobs[i]
            if job.remaining <= 0:
                completed.append(
                    ProductionOutput(job_type=job.job_type, quantity=job.quantity, stop_at=job.stop_at)
                )
                self.jobs.pop(i)
        completed.reverse()
        return completed

    def get_eta_summary(self) -> list[tuple[str, int, int, str]]:
        """Get summary of jobs with ETAs. Returns list of (type, quantity, eta_days, stop_at)."""
        if self.queue_policy != "parallel":
            raise ValueError(f"Unsupported production queue policy: {self.queue_policy}")
        if self.capacity <= 0:
            logger.warning("Production capacity is zero; ETA will be unknown.")
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
