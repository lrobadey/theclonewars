"""Tests for barracks system."""

from clone_wars.engine.barracks import BarracksJobType, BarracksState
from clone_wars.engine.types import LocationId


def test_barracks_state_new() -> None:
    barracks = BarracksState.new(barracks=2, slots_per_barracks=20)
    assert barracks.barracks == 2
    assert barracks.capacity == 40
    assert barracks.jobs == []


def test_barracks_queue_job() -> None:
    barracks = BarracksState.new(barracks=1, slots_per_barracks=10)
    barracks.queue_job(BarracksJobType.INFANTRY, quantity=7)
    assert len(barracks.jobs) == 1
    job = barracks.jobs[0]
    assert job.job_type == BarracksJobType.INFANTRY
    assert job.remaining == 7
    assert job.stop_at == LocationId.NEW_SYSTEM_CORE


def test_barracks_eta_matches_tick() -> None:
    barracks = BarracksState.new(barracks=1, slots_per_barracks=5)
    barracks.queue_job(BarracksJobType.INFANTRY, quantity=6)  # 6 work
    barracks.queue_job(BarracksJobType.SUPPORT, quantity=2)   # 20 work

    eta_summary = barracks.get_eta_summary()
    eta_days = [eta for _, _, eta, _ in eta_summary]

    actual_days: list[int] = []
    day = 0
    while len(actual_days) < len(eta_days):
        day += 1
        completed = barracks.tick()
        for _ in completed:
            actual_days.append(day)

    assert actual_days == eta_days


def test_barracks_redistributes_unused_capacity() -> None:
    costs = {"infantry": 1, "support": 10}
    barracks = BarracksState.new(barracks=1, slots_per_barracks=5, costs=costs)
    barracks.queue_job(BarracksJobType.INFANTRY, quantity=2)  # 2 work
    barracks.queue_job(BarracksJobType.SUPPORT, quantity=10)  # 100 work

    barracks.tick()

    # Infantry finishes early, unused capacity should roll into support job.
    assert barracks.jobs[0].job_type == BarracksJobType.SUPPORT
    assert barracks.jobs[0].remaining == 97
