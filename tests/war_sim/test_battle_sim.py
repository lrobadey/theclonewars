from __future__ import annotations

from tests.helpers.factories import make_state
from war_sim.domain.ops_models import OperationTarget
from war_sim.domain.types import Supplies


def _configure_baseline(state) -> None:
    state.task_force.composition.infantry = 180
    state.task_force.composition.walkers = 3
    state.task_force.composition.support = 4
    state.contested_planet.enemy.infantry = 180
    state.contested_planet.enemy.walkers = 3
    state.contested_planet.enemy.support = 3
    state.contested_planet.enemy.fortification = 1.2


def test_shortage_increases_losses() -> None:
    full = make_state(seed=17, apply=_configure_baseline)
    full.set_front_supplies(Supplies(ammo=400, fuel=300, med_spares=200))

    low = make_state(seed=17, apply=_configure_baseline)
    low.set_front_supplies(Supplies(ammo=40, fuel=300, med_spares=200))

    report_full = full.raid(OperationTarget.FOUNDRY)
    report_low = low.raid(OperationTarget.FOUNDRY)

    assert report_low.losses >= report_full.losses


def test_walker_screen_reduces_infantry_losses() -> None:
    def with_extra_walkers(state):
        _configure_baseline(state)
        state.task_force.composition.walkers = 8

    def no_walkers(state):
        _configure_baseline(state)
        state.task_force.composition.walkers = 0

    with_walkers = make_state(seed=23, apply=with_extra_walkers)
    without_walkers = make_state(seed=23, apply=no_walkers)

    with_walkers.raid(OperationTarget.FOUNDRY)
    without_walkers.raid(OperationTarget.FOUNDRY)

    assert with_walkers.task_force.composition.infantry >= without_walkers.task_force.composition.infantry


def test_medics_improve_readiness_recovery() -> None:
    def with_extra_medics(state):
        _configure_baseline(state)
        state.task_force.composition.support = 8

    def no_medics(state):
        _configure_baseline(state)
        state.task_force.composition.support = 0

    with_medics = make_state(seed=31, apply=with_extra_medics)
    without_medics = make_state(seed=31, apply=no_medics)

    with_medics.raid(OperationTarget.FOUNDRY)
    without_medics.raid(OperationTarget.FOUNDRY)

    assert with_medics.task_force.readiness >= without_medics.task_force.readiness


def test_unified_raid_operation_deterministic() -> None:
    first = make_state(seed=99, apply=_configure_baseline)
    second = make_state(seed=99, apply=_configure_baseline)

    report1 = first.raid(OperationTarget.FOUNDRY)
    report2 = second.raid(OperationTarget.FOUNDRY)

    assert report1.outcome == report2.outcome
    assert report1.days == report2.days
    assert report1.losses == report2.losses
    assert report1.enemy_losses == report2.enemy_losses
    assert [f.name for f in report1.top_factors] == [f.name for f in report2.top_factors]
