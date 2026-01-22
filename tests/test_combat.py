import random

from clone_wars.engine.combat import calculate_power, execute_raid, start_raid_session
from clone_wars.engine.state import GameState


def test_power_calculation() -> None:
    power = calculate_power(100, 2, 1, cohesion=1.0)
    assert power == 110.5


def test_power_with_cohesion() -> None:
    power = calculate_power(100, 2, 1, cohesion=0.5)
    assert power == 55.25


def test_fortification_bonus() -> None:
    power = calculate_power(100, 0, 0, cohesion=1.0, fortification=1.5)
    assert power == 150.0


def test_raid_equal_forces_last_multiple_ticks() -> None:
    state = GameState.new(seed=42)
    state.task_force.composition.infantry = 100
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.contested_planet.enemy.infantry = 100
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    result = execute_raid(state, random.Random(42))
    assert result.ticks >= 6


def test_superior_force_wins() -> None:
    state = GameState.new(seed=42)
    state.task_force.composition.infantry = 200
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.contested_planet.enemy.infantry = 50
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    result = execute_raid(state, random.Random(42))
    assert result.outcome == "VICTORY"


def test_fortification_affects_combat_power_in_raid() -> None:
    base = GameState.new(seed=42)
    base.task_force.composition.infantry = 100
    base.task_force.composition.walkers = 0
    base.task_force.composition.support = 0
    base.contested_planet.enemy.infantry = 100
    base.contested_planet.enemy.walkers = 0
    base.contested_planet.enemy.support = 0
    base.contested_planet.enemy.fortification = 1.0

    fortified = GameState.new(seed=42)
    fortified.task_force.composition.infantry = 100
    fortified.task_force.composition.walkers = 0
    fortified.task_force.composition.support = 0
    fortified.contested_planet.enemy.infantry = 100
    fortified.contested_planet.enemy.walkers = 0
    fortified.contested_planet.enemy.support = 0
    fortified.contested_planet.enemy.fortification = 1.5

    result1 = execute_raid(base, random.Random(42))
    result2 = execute_raid(fortified, random.Random(42))
    assert result1.tick_log
    assert result2.tick_log
    assert result2.tick_log[0].enemy_power > result1.tick_log[0].enemy_power


def test_raid_session_matches_execute_raid() -> None:
    state = GameState.new(seed=42)
    rng_session = random.Random(42)
    rng_execute = random.Random(42)

    session = start_raid_session(state, rng_session)
    while session.outcome is None:
        session.step()
    result_session = session.to_result()

    result_execute = execute_raid(state, rng_execute)

    assert result_session.outcome == result_execute.outcome
    assert result_session.ticks == result_execute.ticks
    assert result_session.tick_log == result_execute.tick_log
    assert result_session.your_remaining == result_execute.your_remaining
    assert result_session.enemy_remaining == result_execute.enemy_remaining
