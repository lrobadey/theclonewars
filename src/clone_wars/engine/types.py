from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ObjectiveStatus(str, Enum):
    ENEMY = "enemy"
    CONTESTED = "contested"
    SECURED = "secured"


@dataclass(frozen=True, slots=True)
class Supplies:
    ammo: int
    fuel: int
    med_spares: int

    def clamp_non_negative(self) -> "Supplies":
        return Supplies(
            ammo=max(0, self.ammo),
            fuel=max(0, self.fuel),
            med_spares=max(0, self.med_spares),
        )


@dataclass(frozen=True, slots=True)
class UnitStock:
    infantry: int
    walkers: int
    support: int

    def clamp_non_negative(self) -> "UnitStock":
        return UnitStock(
            infantry=max(0, self.infantry),
            walkers=max(0, self.walkers),
            support=max(0, self.support),
        )
