"""Tests for production system."""

from clone_wars.engine.production import ProductionJobType, ProductionState


def test_production_state_new() -> None:
    """Test creating new production state."""
    prod = ProductionState.new(capacity=3)
    assert prod.capacity == 3
    assert len(prod.jobs) == 0


def test_queue_job() -> None:
    """Test queueing a production job."""
    prod = ProductionState.new(capacity=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=10)
    assert len(prod.jobs) == 1
    job = prod.jobs[0]
    assert job.job_type == ProductionJobType.AMMO
    assert job.quantity == 10
    assert job.days_remaining > 0


def test_production_tick() -> None:
    """Test production daily tick completes jobs."""
    prod = ProductionState.new(capacity=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=6)  # Should take 2 days with capacity 3

    job = prod.jobs[0]
    days_needed = job.days_remaining

    # Tick until completion
    completed = []
    for _ in range(days_needed):
        completed.extend(prod.tick())

    # Job should be complete
    assert len(prod.jobs) == 0
    assert len(completed) == 1
    assert completed[0] == (ProductionJobType.AMMO, 6)


def test_get_eta_summary() -> None:
    """Test getting ETA summary."""
    prod = ProductionState.new(capacity=3)
    prod.queue_job(ProductionJobType.FUEL, quantity=9)
    prod.queue_job(ProductionJobType.MED_SPARES, quantity=5)

    summary = prod.get_eta_summary()
    assert len(summary) == 2
    assert summary[0][0] == "fuel"
    assert summary[1][0] == "med_spares"

