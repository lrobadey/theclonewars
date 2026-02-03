from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from war_sim.systems.production import ProductionJobType, ProductionState


@given(
    factories=st.integers(min_value=1, max_value=5),
    quantities=st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=4),
)
@settings(max_examples=30)
def test_production_work_conservation(factories: int, quantities: list[int]) -> None:
    prod = ProductionState.new(factories=factories)

    for qty in quantities:
        prod.queue_job(ProductionJobType.AMMO, quantity=qty)

    before_total = sum(job.remaining for job in prod.jobs)
    prod.tick()
    after_total = sum(job.remaining for job in prod.jobs)

    assert after_total <= before_total
    assert before_total - after_total <= prod.capacity
    assert all(job.remaining >= 0 for job in prod.jobs)


@given(
    factories=st.integers(min_value=1, max_value=5),
    quantities=st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=3),
)
@settings(max_examples=30)
def test_production_eta_monotonic_with_more_capacity(
    factories: int, quantities: list[int]
) -> None:
    prod = ProductionState.new(factories=factories)
    for qty in quantities:
        prod.queue_job(ProductionJobType.FUEL, quantity=qty)

    eta_before = [eta for _, _, eta, _ in prod.get_eta_summary()]

    if prod.can_add_factory():
        prod.add_factory(1)
        eta_after = [eta for _, _, eta, _ in prod.get_eta_summary()]
        assert max(eta_after) <= max(eta_before)
