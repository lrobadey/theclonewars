from __future__ import annotations

from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.state import GameState


def _configure_baseline(state: GameState) -> None:
    state.task_force.composition.infantry = 180
    state.task_force.composition.walkers = 3
    state.task_force.composition.support = 4
    state.contested_planet.enemy.infantry = 180
    state.contested_planet.enemy.walkers = 3
    state.contested_planet.enemy.support = 3
    state.contested_planet.enemy.fortification = 1.2


def test_shortage_increases_losses() -> None:
    full = GameState.new(seed=17)
    _configure_baseline(full)
    full.set_front_supplies(type(full.front_supplies)(ammo=400, fuel=300, med_spares=200))

    low = GameState.new(seed=17)
    _configure_baseline(low)
    low.set_front_supplies(type(low.front_supplies)(ammo=40, fuel=300, med_spares=200))

    report_full = full.raid(OperationTarget.FOUNDRY)
    report_low = low.raid(OperationTarget.FOUNDRY)

    assert report_low.losses >= report_full.losses


def test_walker_screen_reduces_infantry_losses() -> None:
    with_walkers = GameState.new(seed=23)
    _configure_baseline(with_walkers)
    with_walkers.task_force.composition.walkers = 8

    without_walkers = GameState.new(seed=23)
    _configure_baseline(without_walkers)
    without_walkers.task_force.composition.walkers = 0

    with_walkers.raid(OperationTarget.FOUNDRY)
    without_walkers.raid(OperationTarget.FOUNDRY)

    assert with_walkers.task_force.composition.infantry >= without_walkers.task_force.composition.infantry


def test_medics_improve_readiness_recovery() -> None:
    with_medics = GameState.new(seed=31)
    _configure_baseline(with_medics)
    with_medics.task_force.composition.support = 8

    without_medics = GameState.new(seed=31)
    _configure_baseline(without_medics)
    without_medics.task_force.composition.support = 0

    with_medics.raid(OperationTarget.FOUNDRY)
    without_medics.raid(OperationTarget.FOUNDRY)

    assert with_medics.task_force.readiness >= without_medics.task_force.readiness


def test_unified_raid_operation_deterministic() -> None:
    first = GameState.new(seed=99)
    second = GameState.new(seed=99)
    _configure_baseline(first)
    _configure_baseline(second)

    report1 = first.raid(OperationTarget.FOUNDRY)
    report2 = second.raid(OperationTarget.FOUNDRY)

    assert report1.outcome == report2.outcome
    assert report1.days == report2.days
    assert report1.losses == report2.losses
    assert report1.enemy_losses == report2.enemy_losses
    assert [factor.name for factor in report1.top_factors] == [factor.name for factor in report2.top_factors]
