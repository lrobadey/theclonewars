from clone_wars.engine.combat import calculate_power
from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.state import GameState


def test_power_calculation() -> None:
    power = calculate_power(100, 2, 1, cohesion=1.0)
    expected = calculate_power(100, 2, 1, cohesion=1.0)
    assert power == expected


def test_power_with_cohesion() -> None:
    power = calculate_power(100, 2, 1, cohesion=0.5)
    expected = calculate_power(100, 2, 1, cohesion=0.5)
    assert power == expected


def test_fortification_bonus() -> None:
    power = calculate_power(100, 0, 0, cohesion=1.0, fortification=1.5)
    expected = calculate_power(100, 0, 0, cohesion=1.0, fortification=1.5)
    assert power == expected


def test_raid_operation_generates_multi_day_ticks() -> None:
    state = GameState.new(seed=42)
    state.task_force.composition.infantry = 100
    state.contested_planet.enemy.infantry = 100
    report = state.raid(OperationTarget.FOUNDRY)

    phase_days = sum(len(phase.days) for phase in report.phases)
    assert phase_days >= 3
    assert report.days >= 3


def test_superior_force_wins() -> None:
    state = GameState.new(seed=42)
    state.task_force.composition.infantry = 200
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.contested_planet.enemy.infantry = 50
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    report = state.raid(OperationTarget.FOUNDRY)
    assert report.outcome in {"CAPTURED", "RAIDED", "DESTROYED"}


def test_fortification_reduces_initial_advantage() -> None:
    base = GameState.new(seed=42)
    base.task_force.composition.infantry = 100
    base.contested_planet.enemy.infantry = 100
    base.contested_planet.enemy.fortification = 1.0

    fortified = GameState.new(seed=42)
    fortified.task_force.composition.infantry = 100
    fortified.contested_planet.enemy.infantry = 100
    fortified.contested_planet.enemy.fortification = 1.5

    report1 = base.raid(OperationTarget.FOUNDRY)
    report2 = fortified.raid(OperationTarget.FOUNDRY)

    day1_base = report1.phases[0].days[0]
    day1_fortified = report2.phases[0].days[0]
    assert day1_fortified.your_advantage < day1_base.your_advantage


def test_raid_determinism_same_seed_same_setup() -> None:
    state1 = GameState.new(seed=42)
    state2 = GameState.new(seed=42)

    for state in (state1, state2):
        state.task_force.composition.infantry = 120
        state.task_force.composition.walkers = 1
        state.task_force.composition.support = 1
        state.contested_planet.enemy.infantry = 110
        state.contested_planet.enemy.walkers = 1
        state.contested_planet.enemy.support = 1

    report1 = state1.raid(OperationTarget.FOUNDRY)
    report2 = state2.raid(OperationTarget.FOUNDRY)

    assert report1.outcome == report2.outcome
    assert report1.days == report2.days
    assert report1.losses == report2.losses
    assert report1.enemy_losses == report2.enemy_losses
    assert [factor.name for factor in report1.top_factors] == [factor.name for factor in report2.top_factors]
