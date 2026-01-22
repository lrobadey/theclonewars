"""Comprehensive tests for production system."""

import math

from clone_wars.engine.types import LocationId
from clone_wars.engine.production import ProductionJobType, ProductionState


def test_production_capacity_variations() -> None:
    """Test production with different capacity values."""
    for factories in [1, 3, 5, 10]:
        prod = ProductionState.new(factories=factories)
        assert prod.factories == factories
        assert prod.capacity == factories * 20  # Default 20 slots per factory
        assert len(prod.jobs) == 0


def test_production_job_duration_calculation() -> None:
    """Test that job duration is calculated correctly based on capacity."""
    # Capacity 3 factories = 60 slots.
    # AMMO cost 20. 6 units = 120 work.
    # 120/60 = 2 days.
    prod = ProductionState.new(factories=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=6)
    summary = prod.get_eta_summary()
    assert summary[0][2] == 2

    # 10 units = 200 work.
    # 200/60 = 3.33 -> 4 days.
    prod = ProductionState.new(factories=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=10)
    summary = prod.get_eta_summary()
    assert summary[0][2] == 4

    # Capacity 5 factories = 100 slots.
    # FUEL cost 20. 12 units = 240 work.
    # 240/100 = 2.4 -> 3 days.
    prod = ProductionState.new(factories=5)
    prod.queue_job(ProductionJobType.FUEL, quantity=12)
    summary = prod.get_eta_summary()
    assert summary[0][2] == 3


def test_production_single_unit_job() -> None:
    """Test production job with single unit."""
    # Cap 60. Work 20. 0.33 days -> 1 day.
    prod = ProductionState.new(factories=3)
    prod.queue_job(ProductionJobType.MED_SPARES, quantity=1)
    summary = prod.get_eta_summary()
    assert summary[0][2] == 1  # Should take at least 1 day


def test_production_multiple_jobs_queue() -> None:
    """Test multiple jobs in queue."""
    prod = ProductionState.new(factories=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=6)
    prod.queue_job(ProductionJobType.FUEL, quantity=9)
    prod.queue_job(ProductionJobType.MED_SPARES, quantity=5)

    assert len(prod.jobs) == 3
    assert prod.jobs[0].job_type == ProductionJobType.AMMO
    assert prod.jobs[1].job_type == ProductionJobType.FUEL
    assert prod.jobs[2].job_type == ProductionJobType.MED_SPARES


def test_production_parallel_completion() -> None:
    """Test that jobs complete in parallel across slots."""
    prod = ProductionState.new(factories=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=3)
    prod.queue_job(ProductionJobType.FUEL, quantity=6)

    # First tick: both jobs in progress
    completed = prod.tick()
    assert len(completed) == 0
    assert len(prod.jobs) == 2

    # Second tick: first job completes, second still in progress
    completed = prod.tick()
    assert len(completed) == 1
    assert completed[0].job_type == ProductionJobType.AMMO
    assert len(prod.jobs) == 1

    # Third tick: second job completes
    completed = prod.tick()
    assert len(completed) == 1
    assert completed[0].job_type == ProductionJobType.FUEL
    assert completed[0].quantity == 6
    assert len(prod.jobs) == 0


def test_production_large_job() -> None:
    """Test production of large quantity job."""
    prod = ProductionState.new(factories=3) # 60 cap
    prod.queue_job(ProductionJobType.AMMO, quantity=100) # 2000 work

    summary = prod.get_eta_summary()
    days_needed = summary[0][2]
    assert days_needed == 34  # ceil(2000/60) = 33.33 -> 34

    # Complete the job
    completed = []
    for _ in range(days_needed):
        completed.extend(prod.tick())

    assert len(completed) == 1
    assert completed[0].job_type == ProductionJobType.AMMO
    assert completed[0].quantity == 100


def test_production_empty_tick() -> None:
    """Test production tick with no jobs."""
    prod = ProductionState.new(factories=3)
    completed = prod.tick()
    assert len(completed) == 0
    assert len(prod.jobs) == 0


def test_production_eta_summary_order() -> None:
    """Test that ETA summary maintains job order."""
    prod = ProductionState.new(factories=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=6)  # 2 days
    prod.queue_job(ProductionJobType.FUEL, quantity=9)  # 3 days
    prod.queue_job(ProductionJobType.MED_SPARES, quantity=5)  # 2 days

    summary = prod.get_eta_summary()
    assert len(summary) == 3
    assert summary[0][0] == "ammo"
    assert summary[1][0] == "fuel"
    assert summary[2][0] == "med_spares"


def test_production_eta_summary_updates() -> None:
    """Test that ETA summary updates as jobs progress."""
    prod = ProductionState.new(factories=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=6)  # 2 days

    summary = prod.get_eta_summary()
    assert summary[0][2] == 2  # days_remaining

    prod.tick()
    summary = prod.get_eta_summary()
    assert summary[0][2] == 1  # days_remaining decreased


def test_production_all_job_types() -> None:
    """Test all production job types."""
    prod = ProductionState.new(factories=3)

    for job_type in ProductionJobType:
        prod.queue_job(job_type, quantity=6)

    assert len(prod.jobs) == len(ProductionJobType)
    job_types = {job.job_type for job in prod.jobs}
    assert job_types == set(ProductionJobType)


def test_production_zero_capacity_edge_case() -> None:
    """Test production with capacity 1 (minimum)."""
    # capacity=1 means 1 factory -> 20 slots
    # Qty 5 -> work 100
    # 100/20 = 5 days.
    prod = ProductionState.new(factories=1)
    prod.queue_job(ProductionJobType.AMMO, quantity=5)
    summary = prod.get_eta_summary()
    assert summary[0][2] == 5


def test_production_job_preserves_quantity() -> None:
    """Test that job quantity is preserved through completion."""
    prod = ProductionState.new(factories=3)
    quantity = 15
    prod.queue_job(ProductionJobType.FUEL, quantity=quantity)

    job = prod.jobs[0]
    assert job.quantity == quantity
    assert job.stop_at == LocationId.NEW_SYSTEM_CORE

    # Complete job
    # Cost 20. Work = 15 * 20 = 300.
    # Cap 60.
    # Days = 300 / 60 = 5.
    days = int(math.ceil((quantity * 20) / prod.capacity))
    completed = []
    for _ in range(days):
        completed.extend(prod.tick())

    assert len(completed) == 1
    assert completed[0].quantity == quantity  # Quantity preserved


def test_production_eta_matches_tick() -> None:
    prod = ProductionState.new(factories=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=6)
    prod.queue_job(ProductionJobType.FUEL, quantity=9)
    prod.queue_job(ProductionJobType.MED_SPARES, quantity=5)

    eta_summary = prod.get_eta_summary()
    eta_days = [eta for _, _, eta, _ in eta_summary]

    actual_days: list[int] = []
    day = 0
    while len(actual_days) < len(eta_days):
        day += 1
        completed = prod.tick()
        for _ in completed:
            actual_days.append(day)

    assert actual_days == eta_days


def test_production_redistributes_unused_capacity() -> None:
    costs = {
        "ammo": 1,
        "fuel": 10,
        "med_spares": 10,
        "walkers": 10,
    }
    prod = ProductionState.new(factories=1, slots_per_factory=5, costs=costs)
    prod.queue_job(ProductionJobType.AMMO, quantity=2)   # 2 work
    prod.queue_job(ProductionJobType.FUEL, quantity=10)  # 100 work

    prod.tick()

    assert prod.jobs[0].job_type == ProductionJobType.FUEL
    assert prod.jobs[0].remaining == 97
