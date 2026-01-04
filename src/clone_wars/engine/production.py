"""Production system: queues, jobs, and output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from clone_wars.engine.types import Supplies


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
    days_remaining: int
    total_days: int


@dataclass(slots=True)
class ProductionState:
    """Production system state."""

    capacity: int
    jobs: list[ProductionJob]

    @staticmethod
    def new(capacity: int = 3) -> ProductionState:
        """Create initial production state."""
        return ProductionState(capacity=capacity, jobs=[])

    def queue_job(self, job_type: ProductionJobType, quantity: int) -> None:
        """Queue a new production job."""
        # Calculate days needed based on capacity
        days_needed = max(1, (quantity + self.capacity - 1) // self.capacity)
        job = ProductionJob(
            job_type=job_type,
            quantity=quantity,
            days_remaining=days_needed,
            total_days=days_needed,
        )
        self.jobs.append(job)

    def tick(self) -> list[tuple[ProductionJobType, int]]:
        """Advance production by one day. Returns list of (job_type, quantity) completed."""
        completed: list[tuple[ProductionJobType, int]] = []
        remaining_jobs: list[ProductionJob] = []

        # Process jobs in order
        for job in self.jobs:
            job.days_remaining -= 1
            if job.days_remaining <= 0:
                # Job complete
                completed.append((job.job_type, job.quantity))
            else:
                remaining_jobs.append(job)

        self.jobs = remaining_jobs
        return completed

    def get_eta_summary(self) -> list[tuple[str, int, int]]:
        """Get summary of jobs with ETAs. Returns list of (type, quantity, days_remaining)."""
        return [(job.job_type.value, job.quantity, job.days_remaining) for job in self.jobs]
