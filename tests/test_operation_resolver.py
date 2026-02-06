"""Tests for the unified operation battle resolver and state effects."""

from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.state import GameState
from clone_wars.engine.types import ObjectiveStatus


def test_raid_consumes_supplies() -> None:
    state = GameState.new(seed=1)
    state.contested_planet.enemy.infantry = 1
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    initial = state.front_supplies
    report = state.raid(OperationTarget.FOUNDRY)

    assert state.front_supplies.ammo <= initial.ammo
    assert state.front_supplies.fuel <= initial.fuel
    assert state.front_supplies.med_spares <= initial.med_spares
    assert report.remaining_supplies == state.front_supplies


def test_raid_applies_casualties_to_both_sides() -> None:
    state = GameState.new(seed=42)
    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.contested_planet.enemy.infantry = 1000
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    report = state.raid(OperationTarget.FOUNDRY)

    assert report.losses > 0
    assert report.enemy_losses > 0
    assert state.task_force.composition.infantry < 1000
    assert state.contested_planet.enemy.infantry < 1000


def test_raid_progresses_objective_on_victory() -> None:
    state = GameState.new(seed=7)
    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.contested_planet.enemy.infantry = 10
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    report = state.raid(OperationTarget.FOUNDRY)
    assert report.outcome in {"CAPTURED", "RAIDED", "DESTROYED"}
    assert state.contested_planet.objectives.foundry in {ObjectiveStatus.CONTESTED, ObjectiveStatus.SECURED}
