"""Tests for the raid-based battle resolver and state effects."""

from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.state import GameState
from clone_wars.engine.types import ObjectiveStatus, Supplies


def test_raid_consumes_supplies() -> None:
    state = GameState.new(seed=1)
    state.planet.enemy.infantry = 1
    state.planet.enemy.walkers = 0
    state.planet.enemy.support = 0
    state.planet.enemy.fortification = 1.0

    initial = state.task_force.supplies
    report = state.raid(OperationTarget.FOUNDRY)

    assert report.supplies_used == Supplies(ammo=50, fuel=30, med_spares=15)
    assert state.task_force.supplies == Supplies(
        ammo=initial.ammo - 50,
        fuel=initial.fuel - 30,
        med_spares=initial.med_spares - 15,
    )


def test_raid_applies_casualties_to_both_sides() -> None:
    state = GameState.new(seed=42)
    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.planet.enemy.infantry = 1000
    state.planet.enemy.walkers = 0
    state.planet.enemy.support = 0
    state.planet.enemy.fortification = 1.0

    report = state.raid(OperationTarget.FOUNDRY)

    assert report.your_casualties > 0
    assert report.enemy_casualties > 0
    assert state.task_force.composition.infantry == report.your_remaining["infantry"]
    assert state.planet.enemy.infantry == report.enemy_remaining["infantry"]


def test_raid_progresses_objective_on_victory() -> None:
    state = GameState.new(seed=7)
    state.task_force.composition.infantry = 1000
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 0
    state.planet.enemy.infantry = 10
    state.planet.enemy.walkers = 0
    state.planet.enemy.support = 0
    state.planet.enemy.fortification = 1.0

    report1 = state.raid(OperationTarget.FOUNDRY)
    assert report1.outcome == "VICTORY"
    assert state.planet.objectives.foundry == ObjectiveStatus.CONTESTED

    report2 = state.raid(OperationTarget.FOUNDRY)
    assert report2.outcome == "VICTORY"
    assert state.planet.objectives.foundry == ObjectiveStatus.SECURED

