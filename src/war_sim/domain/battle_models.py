"""Battle simulator runtime models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass()
class BattleSideState:
    infantry: int
    walkers: int
    support: int
    readiness: float
    cohesion: float

    def total_units(self) -> int:
        return max(0, self.infantry) + max(0, self.walkers) + max(0, self.support)

    def clamp(self) -> None:
        self.infantry = max(0, self.infantry)
        self.walkers = max(0, self.walkers)
        self.support = max(0, self.support)
        self.readiness = min(1.0, max(0.0, self.readiness))
        self.cohesion = min(1.0, max(0.0, self.cohesion))


@dataclass(frozen=True)
class BattleSupplySnapshot:
    ammo_before: int
    fuel_before: int
    med_before: int
    ammo_spent: int
    fuel_spent: int
    med_spent: int
    ammo_ratio: float
    fuel_ratio: float
    med_ratio: float
    shortage_flags: list[str]


@dataclass(frozen=True)
class BattleDayTick:
    day_index: int
    global_day: int
    phase: str
    your_power: float
    enemy_power: float
    your_advantage: float
    initiative: bool
    progress_delta: float
    your_losses: dict[str, int]
    enemy_losses: dict[str, int]
    your_remaining: dict[str, int]
    enemy_remaining: dict[str, int]
    your_cohesion: float
    enemy_cohesion: float
    supplies: BattleSupplySnapshot
    tags: list[str]


@dataclass()
class BattlePhaseAccumulator:
    days: list[BattleDayTick] = field(default_factory=list)
    progress_delta: float = 0.0
    losses: int = 0
    enemy_losses: int = 0
    supplies_spent: dict[str, int] = field(default_factory=lambda: {"ammo": 0, "fuel": 0, "med_spares": 0})
    readiness_delta: float = 0.0
    cohesion_delta: float = 0.0
    enemy_cohesion_delta: float = 0.0

    def add_day(self, tick: BattleDayTick, *, readiness_delta: float = 0.0, cohesion_delta: float = 0.0, enemy_cohesion_delta: float = 0.0) -> None:
        self.days.append(tick)
        self.progress_delta += tick.progress_delta
        self.losses += sum(tick.your_losses.values())
        self.enemy_losses += sum(tick.enemy_losses.values())
        self.supplies_spent["ammo"] += tick.supplies.ammo_spent
        self.supplies_spent["fuel"] += tick.supplies.fuel_spent
        self.supplies_spent["med_spares"] += tick.supplies.med_spent
        self.readiness_delta += readiness_delta
        self.cohesion_delta += cohesion_delta
        self.enemy_cohesion_delta += enemy_cohesion_delta

    def reset(self) -> None:
        self.days.clear()
        self.progress_delta = 0.0
        self.losses = 0
        self.enemy_losses = 0
        self.supplies_spent = {"ammo": 0, "fuel": 0, "med_spares": 0}
        self.readiness_delta = 0.0
        self.cohesion_delta = 0.0
        self.enemy_cohesion_delta = 0.0
