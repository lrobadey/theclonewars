"""Tests for the raid-based battle resolver and state effects."""

from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.state import GameState
from clone_wars.engine.types import ObjectiveStatus, Supplies


def test_raid_consumes_supplies() -> None:
    state = GameState.new(seed=1)
    state.contested_planet.enemy.infantry = 1
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    initial = state.front_supplies
    report = state.raid(OperationTarget.FOUNDRY)

    assert report.supplies_used.ammo >= 0
    assert report.supplies_used.fuel >= 0
    assert report.supplies_used.med_spares >= 0
    assert state.front_supplies == Supplies(
        ammo=initial.ammo - report.supplies_used.ammo,
        fuel=initial.fuel - report.supplies_used.fuel,
        med_spares=initial.med_spares - report.supplies_used.med_spares,
    )


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

    assert report.your_casualties > 0
    assert report.enemy_casualties > 0
    assert state.task_force.composition.infantry == report.your_remaining["infantry"]
    assert state.contested_planet.enemy.infantry == report.enemy_remaining["infantry"]


def test_raid_progresses_objective_on_victory() -> None:
    state = GameState.new(seed=7)
    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.contested_planet.enemy.infantry = 10
    state.contested_planet.enemy.walkers = 0
    state.contested_planet.enemy.support = 0
    state.contested_planet.enemy.fortification = 1.0

    report1 = state.raid(OperationTarget.FOUNDRY)
    assert report1.outcome == "VICTORY"
    assert state.contested_planet.objectives.foundry == ObjectiveStatus.CONTESTED

    report2 = state.raid(OperationTarget.FOUNDRY)
    assert report2.outcome == "VICTORY"
    assert state.contested_planet.objectives.foundry == ObjectiveStatus.SECURED
