from __future__ import annotations

from war_sim.domain.types import ObjectiveStatus, Supplies, UnitStock


def assert_supplies_non_negative(supplies: Supplies) -> None:
    assert supplies.ammo >= 0
    assert supplies.fuel >= 0
    assert supplies.med_spares >= 0


def assert_units_non_negative(units: UnitStock) -> None:
    assert units.infantry >= 0
    assert units.walkers >= 0
    assert units.support >= 0


def assert_objective_status(status: ObjectiveStatus) -> None:
    assert status in (
        ObjectiveStatus.ENEMY,
        ObjectiveStatus.CONTESTED,
        ObjectiveStatus.SECURED,
    )


def total_supplies(supplies: Supplies) -> int:
    return supplies.ammo + supplies.fuel + supplies.med_spares


def total_units(units: UnitStock) -> int:
    return units.infantry + units.walkers + units.support
