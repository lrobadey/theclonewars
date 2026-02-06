from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.helpers.factories import make_state
from war_sim.domain.ops_models import OperationTarget
from war_sim.systems.combat import calculate_power


@given(
    base=st.integers(min_value=1, max_value=200),
    delta=st.integers(min_value=0, max_value=200),
    cohesion=st.floats(min_value=0.0, max_value=1.0),
)
@settings(max_examples=40)
def test_calculate_power_monotonic(base: int, delta: int, cohesion: float) -> None:
    p1 = calculate_power(base, 0, 0, cohesion=cohesion)
    p2 = calculate_power(base + delta, 0, 0, cohesion=cohesion)
    assert p2 >= p1


@given(
    seed=st.integers(min_value=1, max_value=1000),
    your_inf=st.integers(min_value=50, max_value=300),
    enemy_inf=st.integers(min_value=50, max_value=300),
)
@settings(max_examples=25)
def test_raid_bounds_and_conservation(seed: int, your_inf: int, enemy_inf: int) -> None:
    def apply(state):
        state.task_force.composition.infantry = your_inf
        state.task_force.composition.walkers = 0
        state.task_force.composition.support = 0
        state.contested_planet.enemy.infantry = enemy_inf
        state.contested_planet.enemy.walkers = 0
        state.contested_planet.enemy.support = 0
        state.contested_planet.enemy.cohesion = 1.0
        state.contested_planet.enemy.fortification = 1.0

    state = make_state(seed=seed, apply=apply)
    initial_you = state.task_force.composition.infantry
    initial_enemy = state.contested_planet.enemy.infantry
    report = state.raid(OperationTarget.FOUNDRY)

    assert report.days >= 1
    assert report.losses >= 0
    assert report.enemy_losses >= 0
    assert state.task_force.composition.infantry <= initial_you
    assert state.contested_planet.enemy.infantry <= initial_enemy
    assert 0.0 <= state.task_force.cohesion <= 1.0
    assert 0.0 <= state.contested_planet.enemy.cohesion <= 1.0


def test_raid_determinism_same_seed() -> None:
    def apply(state):
        state.task_force.composition.infantry = 120
        state.task_force.composition.walkers = 1
        state.task_force.composition.support = 1
        state.contested_planet.enemy.infantry = 110
        state.contested_planet.enemy.walkers = 1
        state.contested_planet.enemy.support = 1

    s1 = make_state(seed=7, apply=apply)
    s2 = make_state(seed=7, apply=apply)

    r1 = s1.raid(OperationTarget.FOUNDRY)
    r2 = s2.raid(OperationTarget.FOUNDRY)

    assert r1.outcome == r2.outcome
    assert r1.days == r2.days
    assert r1.losses == r2.losses
    assert r1.enemy_losses == r2.enemy_losses
