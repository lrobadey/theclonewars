from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from war_sim.systems.barracks import BarracksJobType, BarracksState


@given(
    barracks=st.integers(min_value=1, max_value=5),
    quantities=st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=4),
)
@settings(max_examples=30)
def test_barracks_work_conservation(barracks: int, quantities: list[int]) -> None:
    state = BarracksState.new(barracks=barracks)

    for qty in quantities:
        state.queue_job(BarracksJobType.INFANTRY, quantity=qty)

    before_total = sum(job.remaining for job in state.jobs)
    state.tick()
    after_total = sum(job.remaining for job in state.jobs)

    assert after_total <= before_total
    assert before_total - after_total <= state.capacity
    assert all(job.remaining >= 0 for job in state.jobs)


@given(
    barracks=st.integers(min_value=1, max_value=5),
    quantities=st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=3),
)
@settings(max_examples=30)
def test_barracks_eta_monotonic_with_more_capacity(
    barracks: int, quantities: list[int]
) -> None:
    state = BarracksState.new(barracks=barracks)
    for qty in quantities:
        state.queue_job(BarracksJobType.SUPPORT, quantity=qty)

    eta_before = [eta for _, _, eta, _ in state.get_eta_summary()]

    if state.can_add_barracks():
        state.add_barracks(1)
        eta_after = [eta for _, _, eta, _ in state.get_eta_summary()]
        assert max(eta_after) <= max(eta_before)
