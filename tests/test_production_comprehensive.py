"""Invariant-style tests for production system."""

from clone_wars.engine.production import ProductionJobType, ProductionState
from clone_wars.engine.types import LocationId


def test_production_capacity_invariant() -> None:
    prod = ProductionState.new(factories=3, slots_per_factory=20)
    assert prod.capacity == prod.factories * prod.slots_per_factory


def test_queue_job_preserves_quantity_and_stop() -> None:
    prod = ProductionState.new(factories=2)
    prod.queue_job(ProductionJobType.AMMO, quantity=7, stop_at=LocationId.CONTESTED_MID_DEPOT)
    job = prod.jobs[0]
    assert job.quantity == 7
    assert job.stop_at == LocationId.CONTESTED_MID_DEPOT
    assert job.remaining == 7 * prod.costs[job.job_type.value]


def test_tick_completes_jobs_without_negative_remaining() -> None:
    prod = ProductionState.new(factories=3)
    prod.queue_job(ProductionJobType.AMMO, quantity=6)
    prod.queue_job(ProductionJobType.FUEL, quantity=6)

    while prod.jobs:
        completed = prod.tick()
        assert all(job.remaining >= 0 for job in prod.jobs)
        for output in completed:
            assert output.quantity > 0


def test_eta_summary_matches_completion_order() -> None:
    prod = ProductionState.new(factories=2)
    prod.queue_job(ProductionJobType.AMMO, quantity=3)
    prod.queue_job(ProductionJobType.FUEL, quantity=3)

    eta_summary = {job_type: eta for job_type, _, eta, _ in prod.get_eta_summary()}
    actual_days: dict[str, int] = {}
    day = 0
    while len(actual_days) < len(eta_summary):
        day += 1
        completed = prod.tick()
        for output in completed:
            actual_days[output.job_type.value] = day

    assert actual_days == eta_summary
