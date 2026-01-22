"""Common types and enums."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class FactionId(str, Enum):
    NEW_SYSTEM = "new_system"
    COLLECTIVE = "collective"


class LocationId(str, Enum):
    """Location IDs for the solar system graph."""
    
    # New System Territory
    NEW_SYSTEM_CORE = "new_system_core"
    
    # Transit
    DEEP_SPACE = "deep_space"
    
    # Contested Planet Logistics Chain
    CONTESTED_SPACEPORT = "contested_spaceport"
    CONTESTED_MID_DEPOT = "contested_mid_depot"
    CONTESTED_FRONT = "contested_front"


class ObjectiveStatus(str, Enum):
    ENEMY = "enemy"
    CONTESTED = "contested"
    SECURED = "secured"

@dataclass()
class Objectives:
    foundry: ObjectiveStatus
    comms: ObjectiveStatus
    power: ObjectiveStatus


@dataclass()
class EnemyForce:
    infantry: int
    walkers: int
    support: int
    cohesion: float
    fortification: float
    reinforcement_rate: float
    intel_confidence: float


@dataclass()
class PlanetState:
    objectives: Objectives
    enemy: EnemyForce
    control: float  # 0.0 to 1.0, player control level


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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
