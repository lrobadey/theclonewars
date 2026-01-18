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


PRODUCTION_COSTS: dict[ProductionJobType, int] = {
    ProductionJobType.AMMO: 20,
    ProductionJobType.FUEL: 20,
    ProductionJobType.MED_SPARES: 20,
    ProductionJobType.INFANTRY: 1,
    ProductionJobType.WALKERS: 20,
    ProductionJobType.SUPPORT: 20,
}


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
        slots_per_factory: int = 20,
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
            remaining=quantity * PRODUCTION_COSTS.get(job_type, 20),
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

        # 1. Filter to active jobs
        active_indices = [i for i, job in enumerate(self.jobs) if job.remaining > 0]
        if not active_indices:
            # Clean up completed jobs that might be lingering (though normally popped)
            # This is a safety valve.
            i = 0
            while i < len(self.jobs):
                if self.jobs[i].remaining <= 0:
                    job = self.jobs[i]
                    completed.append(
                        ProductionOutput(job_type=job.job_type, quantity=job.quantity, stop_at=job.stop_at)
                    )
                    self.jobs.pop(i)
                else:
                    i += 1
            return completed

        # 2. Calculate fair share
        capacity_remaining = self.capacity
        count_active = len(active_indices)
        
        # We loop to handle cases where a job needs LESS than its fair share,
        # verifying we redistribute the unused capacity to others.
        # Worst case O(Jobs), usually O(1) loop.
        while count_active > 0 and capacity_remaining > 0:
            base_share = capacity_remaining // count_active
            extra_slots = capacity_remaining % count_active
            
            # Temporary tracking for next iteration
            capacity_spent_this_round = 0
            still_active_indices = []
            
            # We must iterate in order to respect the "extra slots" distribution 
            # (usually the first N jobs get +1 slot).
            # We map active_indices back to the job objects.
            
            # To be strictly deterministic and fair, we give the extra slots to the first N active jobs.
            # But "first" means in queue order.
            
            for i, idx in enumerate(active_indices):
                job = self.jobs[idx]
                
                # Determine allocation for this job in this pass
                allocation = base_share
                if i < extra_slots:
                    allocation += 1
                
                if allocation <= 0:
                    still_active_indices.append(idx)
                    continue

                # Apply allocation
                amount_needed = job.remaining
                amount_used = min(allocation, amount_needed)
                
                job.remaining -= amount_used
                capacity_spent_this_round += amount_used
                
                if job.remaining > 0:
                    still_active_indices.append(idx)
            
            # Update main loop variables
            capacity_remaining -= capacity_spent_this_round
            
            # Optimization: If we spent exactly what we had or everyone is done, break
            if not still_active_indices or capacity_remaining <= 0:
                break
                
            # If we had unused capacity (because some jobs finished capable of taking more),
            # we loop again to redistribute 'capacity_remaining' among 'still_active_indices'.
            # However, we must ensure we don't loop infinitely if no progress is made.
            # In this logic, 'capacity_remaining' strictly decreases or 'active_indices' shrinks.
            if len(still_active_indices) == count_active and capacity_remaining == (self.capacity - capacity_spent_this_round):
                 # Should not happen if math is right, but safety break
                 break
                 
            active_indices = still_active_indices
            count_active = len(active_indices)

        # 3. Collect completed jobs
        # Iterate backwards to safely pop
        for i in range(len(self.jobs) - 1, -1, -1):
            job = self.jobs[i]
            if job.remaining <= 0:
                completed.append(
                    ProductionOutput(job_type=job.job_type, quantity=job.quantity, stop_at=job.stop_at)
                )
                self.jobs.pop(i)

        # Reverse completed list to maintain chronological completion order if multiple finished
        # (Though they all finished "today", the queue order is preserved by the append order above if we reversed handling)
        # Actually, popping from back means the last job is first in 'completed'. 
        # Ideally, we want the first completed job (top of queue) to be first in output.
        completed.reverse()

        return completed

    def get_eta_summary(self) -> list[tuple[str, int, int, str]]:
        """Get summary of jobs with ETAs. Returns list of (type, quantity, eta_days, stop_at)."""
        if self.capacity <= 0:
            raise ValueError("Production capacity must be positive")
        if not self.jobs:
            return []

        # We simulate the mathematical progression without modifying state.
        # To do this O(N) or O(J) accurately for ETAs is complex because 
        # determining exactly which day a job finishes depends on the dynamic "active count" of future days.
        
        # However, we can simulate "days" efficiently. 
        # Instead of single-unit ticks, we can predict "days until next state change".
        
        # Simpler approach for now:
        # Since this is a UI/Explainer helper, a slightly heavier simulation is okay compared to the core tick,
        # but we should still avoid the O(N) internal loop.
        # We will clone the 'remaining' values and simulate day-by-day batch processing.
        
        work_remaining = [job.remaining for job in self.jobs]
        completion_days = [0] * len(self.jobs)
        active_indices = [i for i, val in enumerate(work_remaining) if val > 0]
        day = 0
        
        while active_indices:
            day += 1
            capacity_for_day = self.capacity
            count_active = len(active_indices)
            
            # Distribute capacity for this day
            # We use a similar loop to 'tick' but applied to our local list
            
            current_day_capacity = capacity_for_day
            
            # We loop to redistribute unused capacity within the day
            while count_active > 0 and current_day_capacity > 0:
                base_share = current_day_capacity // count_active
                extra_slots = current_day_capacity % count_active
                
                spent_this_round = 0
                next_active = []
                
                for i, idx in enumerate(active_indices):
                    # In the real tick, indices are relative to the *original* list order (0, 1, 2...)
                    # Here 'enumerate(active_indices)' gives us the priority order 0..N among actives.
                    
                    allocation = base_share
                    if i < extra_slots:
                        allocation += 1
                        
                    if allocation <= 0:
                        next_active.append(idx)
                        continue
                        
                    needed = work_remaining[idx]
                    used = min(allocation, needed)
                    
                    work_remaining[idx] -= used
                    spent_this_round += used
                    
                    if work_remaining[idx] <= 0:
                        if completion_days[idx] == 0:
                            completion_days[idx] = day
                    else:
                        next_active.append(idx)
                
                current_day_capacity -= spent_this_round
                active_indices = next_active
                count_active = len(active_indices)
                
                if not active_indices:
                    break
        
        summary: list[tuple[str, int, int, str]] = []
        for i, job in enumerate(self.jobs):
            # If a job was already done (remaining <= 0), it finishes "Day 1" (or Day 0 basically)
            c_day = completion_days[i]
            if c_day == 0 and job.remaining > 0:
                # Should not happen if logic holds
                c_day = -1 
            elif c_day == 0 and job.remaining <= 0:
                c_day = 1
                
            summary.append((job.job_type.value, job.quantity, c_day, job.stop_at.value))
            
        return summary
