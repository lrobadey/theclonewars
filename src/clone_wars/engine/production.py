"""Production system: queues, jobs, and output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from clone_wars.engine.logistics import DepotNode


class ProductionJobType(str, Enum):
    """Types of production jobs."""

    AMMO = "ammo"
    FUEL = "fuel"
    MED_SPARES = "med_spares"
    INFANTRY = "infantry"
    WALKERS = "walkers"
    SUPPORT = "support"


@dataclass(slots=True)
class ProductionJob:
    """A production job in the queue."""

    job_type: ProductionJobType
    quantity: int
    remaining: int
    stop_at: DepotNode


@dataclass(frozen=True, slots=True)
class ProductionOutput:
    """A completed production output."""

    job_type: ProductionJobType
    quantity: int
    stop_at: DepotNode


@dataclass(slots=True)
class ProductionState:
    """Production system state."""

    factories: int
    slots_per_factory: int
    max_factories: int
    jobs: list[ProductionJob]

    @staticmethod
    def new(
        capacity: int | None = None,
        factories: int = 3,
        slots_per_factory: int = 1,
        max_factories: int = 6,
    ) -> ProductionState:
        """Create initial production state."""
        if capacity is not None:
            factories = capacity
        return ProductionState(
            factories=factories,
            slots_per_factory=slots_per_factory,
            max_factories=max_factories,
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

    def queue_job(
        self, job_type: ProductionJobType, quantity: int, stop_at: DepotNode = DepotNode.CORE
    ) -> None:
        """Queue a new production job."""
        if quantity <= 0:
            raise ValueError("Production quantity must be positive")
        if self.capacity <= 0:
            raise ValueError("Production capacity must be positive")
        job = ProductionJob(
            job_type=job_type,
            quantity=quantity,
            remaining=quantity,
            stop_at=stop_at,
        )
        self.jobs.append(job)

    def tick(self) -> list[ProductionOutput]:
        """Advance production by one day. Returns completed outputs."""
        if self.capacity <= 0:
            raise ValueError("Production capacity must be positive")
        completed: list[ProductionOutput] = []
        if not self.jobs:
            return completed

        capacity_remaining = self.capacity
        index = 0
        while capacity_remaining > 0 and self.jobs:
            if index >= len(self.jobs):
                index = 0
            job = self.jobs[index]
            job.remaining -= 1
            capacity_remaining -= 1
            if job.remaining <= 0:
                completed.append(
                    ProductionOutput(job_type=job.job_type, quantity=job.quantity, stop_at=job.stop_at)
                )
                self.jobs.pop(index)
                continue
            index += 1

        return completed

    def get_eta_summary(self) -> list[tuple[str, int, int, str]]:
        """Get summary of jobs with ETAs. Returns list of (type, quantity, eta_days, stop_at)."""
        if self.capacity <= 0:
            raise ValueError("Production capacity must be positive")
        if not self.jobs:
            return []
        work_remaining = [job.remaining for job in self.jobs]
        completion_days = [0 for _ in self.jobs]
        day = 0
        while any(remaining > 0 for remaining in work_remaining):
            day += 1
            capacity_remaining = self.capacity
            index = 0
            while capacity_remaining > 0 and any(remaining > 0 for remaining in work_remaining):
                if index >= len(work_remaining):
                    index = 0
                if work_remaining[index] <= 0:
                    index += 1
                    continue
                work_remaining[index] -= 1
                capacity_remaining -= 1
                if work_remaining[index] == 0:
                    completion_days[index] = day
                index += 1

        summary: list[tuple[str, int, int, str]] = []
        for job, completion_day in zip(self.jobs, completion_days, strict=True):
            eta_days = max(1, completion_day)
            summary.append((job.job_type.value, job.quantity, eta_days, job.stop_at.value))
        return summary
