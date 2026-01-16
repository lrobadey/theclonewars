"""Production system: queues, jobs, and output."""

from __future__ import annotations

import math
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

    capacity: int
    jobs: list[ProductionJob]

    @staticmethod
    def new(capacity: int = 3) -> ProductionState:
        """Create initial production state."""
        return ProductionState(capacity=capacity, jobs=[])

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

        capacity_remaining = self.capacity
        while capacity_remaining > 0 and self.jobs:
            job = self.jobs[0]
            worked = min(capacity_remaining, job.remaining)
            job.remaining -= worked
            capacity_remaining -= worked
            if job.remaining > 0:
                break
            completed.append(
                ProductionOutput(job_type=job.job_type, quantity=job.quantity, stop_at=job.stop_at)
            )
            self.jobs.pop(0)

        return completed

    def get_eta_summary(self) -> list[tuple[str, int, int, str]]:
        """Get summary of jobs with ETAs. Returns list of (type, quantity, eta_days, stop_at)."""
        if self.capacity <= 0:
            raise ValueError("Production capacity must be positive")
        work_prefix = 0
        summary: list[tuple[str, int, int, str]] = []
        for job in self.jobs:
            work_prefix += job.remaining
            eta_days = int(math.ceil(work_prefix / self.capacity))
            summary.append((job.job_type.value, job.quantity, eta_days, job.stop_at.value))
        return summary
