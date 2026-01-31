from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from schism_sim.engine.rules import GlobalConfig
from schism_sim.engine.types import Supplies

# 1 Walker can effectively screen 20 Infantry.
WALKER_COVERAGE_CAPACITY = 20

if TYPE_CHECKING:
    from schism_sim.engine.state import GameState


class RaidBeat(Enum):
    INFILTRATION = "INFILTRATION"  # ticks 1-3
    BREACH = "BREACH"  # ticks 4-8
    EXFILTRATION = "EXFIL"  # ticks 9-12


def get_beat(tick: int) -> RaidBeat:
    if tick <= 3:
        return RaidBeat.INFILTRATION
    elif tick <= 8:
        return RaidBeat.BREACH
    else:
        return RaidBeat.EXFILTRATION


@dataclass(frozen=True)
class RaidFactor:
    name: str
    value: float
    why: str


@dataclass(frozen=True)
class CombatTick:
    tick: int
    your_power: float
    enemy_power: float
    your_cohesion: float
    enemy_cohesion: float
    your_casualties: int
    enemy_casualties: int
    event: str
    beat: str = ""


@dataclass(frozen=True)
class CombatResult:
    outcome: str
    reason: str
    ticks: int
    your_final_cohesion: float
    enemy_final_cohesion: float
    your_casualties_total: int
    enemy_casualties_total: int
    your_remaining: dict[str, int]
    enemy_remaining: dict[str, int]
    tick_log: list[CombatTick]
    supplies_consumed: Supplies
    top_factors: list[RaidFactor] = field(default_factory=list)


@dataclass()
class RaidCombatSession:
    rng: random.Random
    config: GlobalConfig
    supply_mod: float
    enemy_fortification: float
    supplies_before: Supplies

    your_infantry: int
    your_walkers: int
    your_support: int
    your_cohesion: float

    enemy_infantry: int
    enemy_walkers: int
    enemy_support: int
    enemy_cohesion: float

    max_ticks: int

    ammo_ratio: float = 1.0
    fuel_ratio: float = 1.0
    intel_confidence: float = 0.7

    initial_walkers: int = 0
    tick: int = 0
    your_casualties_total: int = 0
    enemy_casualties_total: int = 0
    tick_log: list[CombatTick] = field(default_factory=list)
    outcome: str | None = None
    reason: str | None = None

    initiative_wins: int = 0
    initiative_losses: int = 0
    ammo_pinch_ticks: int = 0
    walker_screen_saves: int = 0
    fortification_penalty_ticks: int = 0
    enemy_counterattacks: int = 0
    screen_efficiency_total: float = 0.0
    screen_efficiency_ticks: int = 0

    def step(self) -> CombatTick | None:
        if self.outcome is not None:
            return None
        if self.tick >= self.max_ticks:
            self._finalize_stall()
            return None

        tick_num = self.tick + 1
        beat = get_beat(tick_num)

        fort_mod = 1.0
        exfil_pressure = 1.0
        if beat == RaidBeat.INFILTRATION:
            fort_mod = 1.0 + 0.15 * (self.enemy_fortification - 1.0)
            if self.enemy_fortification > 1.0:
                self.fortification_penalty_ticks += 1
        elif beat == RaidBeat.EXFILTRATION:
            exfil_pressure = 1.15

        base_init = 0.5 + 0.2 * (self.ammo_ratio - 0.5) + 0.15 * (self.your_cohesion - 0.5)
        variance_amp = 0.15 * (1.0 - self.intel_confidence)
        init_roll = self.rng.uniform(-variance_amp, variance_amp)
        initiative_score = base_init + init_roll

        you_have_initiative = initiative_score > 0.5
        if you_have_initiative:
            self.initiative_wins += 1
        else:
            self.initiative_losses += 1

        ammo_pinch = self.ammo_ratio < self.config.ammo_pinch_threshold
        if ammo_pinch:
            self.ammo_pinch_ticks += 1

        effective_supply_mod = self.supply_mod
        if ammo_pinch:
            effective_supply_mod *= 0.75

        your_power = calculate_power(
            self.your_infantry,
            self.your_walkers,
            self.your_support,
            self.your_cohesion,
            effective_supply_mod,
        )
        enemy_power = calculate_power(
            self.enemy_infantry,
            self.enemy_walkers,
            self.enemy_support,
            self.enemy_cohesion,
            fortification=self.enemy_fortification * fort_mod,
        )

        if your_power <= 0 and enemy_power <= 0:
            self.outcome = "STALEMATE"
            self.reason = "Both forces exhausted"
            return None
        if your_power <= 0:
            self.outcome = "DEFEAT"
            self.reason = "Your force combat ineffective"
            return None
        if enemy_power <= 0:
            self.outcome = "VICTORY"
            self.reason = "Enemy force combat ineffective"
            return None

        your_advantage = your_power / enemy_power
        enemy_advantage = enemy_power / your_power

        init_damage_bonus = 1.10 if you_have_initiative else 1.0
        init_casualty_penalty = 1.0 if you_have_initiative else 1.05

        your_roll = self.rng.uniform(0.95, 1.05)
        enemy_roll = self.rng.uniform(0.95, 1.05)

        damage_to_enemy_coh = self.config.raid_base_damage_rate * your_advantage * your_roll * init_damage_bonus
        damage_to_you_coh = self.config.raid_base_damage_rate * enemy_advantage * enemy_roll

        enemy_counterattack = False
        if (
            beat == RaidBeat.BREACH
            and not you_have_initiative
            and self.enemy_fortification > 1.1
            and self.your_cohesion < 0.6
        ):
            enemy_counterattack = True
            self.enemy_counterattacks += 1
            damage_to_you_coh *= 1.20

        self.enemy_cohesion = max(0.0, self.enemy_cohesion - damage_to_enemy_coh)
        self.your_cohesion = max(0.0, self.your_cohesion - damage_to_you_coh)

        your_force_size = self.your_infantry + self.your_walkers + self.your_support
        enemy_force_size = self.enemy_infantry + self.enemy_walkers + self.enemy_support

        cas_multiplier = init_casualty_penalty * exfil_pressure
        your_cas_target = self._sample_casualties(your_force_size, damage_to_you_coh * cas_multiplier)
        enemy_cas_target = self._sample_casualties(enemy_force_size, damage_to_enemy_coh)

        screen_efficiency = self._calculate_screen_efficiency(self.your_walkers, self.your_infantry)
        self.screen_efficiency_total += screen_efficiency
        self.screen_efficiency_ticks += 1
        walker_screen_active = self.your_walkers > 0
        your_inf_loss, your_walk_loss, your_sup_loss = self._split_casualties_dynamic(
            your_cas_target,
            self.your_infantry,
            self.your_walkers,
            self.your_support,
            screen_efficiency=screen_efficiency,
        )
        your_applied = your_inf_loss + your_walk_loss + your_sup_loss

        if walker_screen_active and your_walk_loss > 0:
            self.walker_screen_saves += your_walk_loss

        self.your_infantry -= your_inf_loss
        self.your_walkers -= your_walk_loss
        self.your_support -= your_sup_loss
        self.your_casualties_total += your_applied

        enemy_inf_loss, enemy_walk_loss, enemy_sup_loss = self._split_casualties(
            enemy_cas_target, self.enemy_infantry, self.enemy_walkers, self.enemy_support
        )
        enemy_applied = enemy_inf_loss + enemy_walk_loss + enemy_sup_loss
        self.enemy_infantry -= enemy_inf_loss
        self.enemy_walkers -= enemy_walk_loss
        self.enemy_support -= enemy_sup_loss
        self.enemy_casualties_total += enemy_applied

        event_parts: list[str] = []
        if you_have_initiative:
            event_parts.append("INITIATIVE WON")
        if ammo_pinch:
            event_parts.append("AMMO PINCH")
        if self.initial_walkers > 0:
            if screen_efficiency >= 1.0:
                event_parts.append("FULL SCREEN")
            elif screen_efficiency < 0.5:
                event_parts.append("SCREEN BUCKLED")
            else:
                event_parts.append("PARTIAL SCREEN")
        if enemy_counterattack:
            event_parts.append("ENEMY COUNTERATTACK")
        if beat == RaidBeat.INFILTRATION and self.enemy_fortification > 1.0:
            event_parts.append("FORTIFICATION -")
        if self.enemy_cohesion < 0.4:
            event_parts.append("Enemy wavering")
        elif self.your_cohesion < 0.4:
            event_parts.append("Under pressure")
        elif your_advantage > 1.2:
            event_parts.append("Pressing attack")
        elif enemy_advantage > 1.2:
            event_parts.append("Resistance stiffens")
        else:
            event_parts.append("Exchange of fire")

        event = f"{beat.value}: " + ", ".join(event_parts)

        self.tick = tick_num
        tick_record = CombatTick(
            tick=tick_num,
            your_power=round(your_power, 1),
            enemy_power=round(enemy_power, 1),
            your_cohesion=round(self.your_cohesion, 2),
            enemy_cohesion=round(self.enemy_cohesion, 2),
            your_casualties=your_applied,
            enemy_casualties=enemy_applied,
            event=event,
            beat=beat.value,
        )
        self.tick_log.append(tick_record)

        if self.enemy_cohesion < 0.2:
            self.outcome = "VICTORY"
            self.reason = f"Enemy broke at {int(self.enemy_cohesion * 100)}% cohesion after {tick_num} ticks"
        elif self.your_cohesion < 0.2:
            self.outcome = "DEFEAT"
            self.reason = f"Your force broke at {int(self.your_cohesion * 100)}% cohesion after {tick_num} ticks"

        if self.tick >= self.max_ticks and self.outcome is None:
            self._finalize_stall()

        return tick_record

    def to_result(self) -> CombatResult:
        if self.outcome is None or self.reason is None:
            self._finalize_stall()

        supplies_consumed = Supplies(
            ammo=min(self.supplies_before.ammo, self.config.raid_ammo_cost),
            fuel=min(self.supplies_before.fuel, self.config.raid_fuel_cost),
            med_spares=min(self.supplies_before.med_spares, self.config.raid_med_cost),
        )

        top_factors = self._build_top_factors()

        return CombatResult(
            outcome=self.outcome,
            reason=self.reason,
            ticks=len(self.tick_log),
            your_final_cohesion=self.your_cohesion,
            enemy_final_cohesion=self.enemy_cohesion,
            your_casualties_total=self.your_casualties_total,
            enemy_casualties_total=self.enemy_casualties_total,
            your_remaining={
                "infantry": self.your_infantry,
                "walkers": self.your_walkers,
                "support": self.your_support,
            },
            enemy_remaining={
                "infantry": self.enemy_infantry,
                "walkers": self.enemy_walkers,
                "support": self.enemy_support,
            },
            tick_log=list(self.tick_log),
            supplies_consumed=supplies_consumed,
            top_factors=top_factors,
        )

    def _build_top_factors(self) -> list[RaidFactor]:
        factors: list[RaidFactor] = []
        total_ticks = len(self.tick_log)
        if total_ticks == 0:
            return factors

        if self.initiative_wins > 0 or self.initiative_losses > 0:
            net_init = self.initiative_wins - self.initiative_losses
            if net_init > 0:
                factors.append(
                    RaidFactor(
                        name="initiative_advantage",
                        value=float(net_init),
                        why=f"Won initiative {self.initiative_wins}/{total_ticks} ticks (+damage, -casualties)",
                    )
                )
            elif net_init < 0:
                factors.append(
                    RaidFactor(
                        name="initiative_deficit",
                        value=float(net_init),
                        why=f"Lost initiative {self.initiative_losses}/{total_ticks} ticks (+casualties)",
                    )
                )

        if self.ammo_pinch_ticks > 0:
            factors.append(
                RaidFactor(
                    name="ammo_pinch",
                    value=float(-self.ammo_pinch_ticks),
                    why=f"Low ammo reduced firepower for {self.ammo_pinch_ticks} ticks",
                )
            )

        if self.walker_screen_saves > 0:
            avg_efficiency = (
                self.screen_efficiency_total / self.screen_efficiency_ticks
                if self.screen_efficiency_ticks > 0
                else 0.0
            )
            avg_percent = round(avg_efficiency * 100)
            factors.append(
                RaidFactor(
                    name="walker_screen",
                    value=float(self.walker_screen_saves),
                    why=(
                        "Walkers provided "
                        f"{avg_percent}% coverage, absorbing {self.walker_screen_saves} casualties"
                    ),
                )
            )

        if self.fortification_penalty_ticks > 0:
            factors.append(
                RaidFactor(
                    name="fortification_penalty",
                    value=float(-self.fortification_penalty_ticks),
                    why=f"Enemy fortification slowed infiltration for {self.fortification_penalty_ticks} ticks",
                )
            )

        if self.enemy_counterattacks > 0:
            factors.append(
                RaidFactor(
                    name="enemy_counterattacks",
                    value=float(-self.enemy_counterattacks),
                    why=f"Enemy counterattacked {self.enemy_counterattacks} times during breach",
                )
            )

        factors.sort(key=lambda f: abs(f.value), reverse=True)
        return factors[:5]

    def _finalize_stall(self) -> None:
        if self.outcome is None:
            self.outcome = "DEFEAT"
            self.reason = f"Raid stalled after {self.max_ticks} ticks, forced to withdraw"

    def _sample_casualties(self, force_size: int, cohesion_damage: float) -> int:
        expected = max(0.0, force_size * cohesion_damage * self.config.raid_casualty_rate)
        whole = int(expected)
        if self.rng.random() < (expected - whole):
            whole += 1
        return whole

    @staticmethod
    def _split_casualties(total: int, infantry: int, walkers: int, support: int) -> tuple[int, int, int]:
        if total <= 0:
            return (0, 0, 0)
        weights = (0.7, 0.2, 0.1)
        raw = (total * weights[0], total * weights[1], total * weights[2])
        inf_loss = min(infantry, int(raw[0]))
        walk_loss = min(walkers, int(raw[1]))
        sup_loss = min(support, int(raw[2]))
        remaining = total - (inf_loss + walk_loss + sup_loss)
        for idx in (0, 1, 2):
            if remaining <= 0:
                break
            if idx == 0:
                cap = infantry - inf_loss
                add = min(cap, remaining)
                inf_loss += add
            elif idx == 1:
                cap = walkers - walk_loss
                add = min(cap, remaining)
                walk_loss += add
            else:
                cap = support - sup_loss
                add = min(cap, remaining)
                sup_loss += add
            remaining -= add
        return (inf_loss, walk_loss, sup_loss)

    def _split_casualties_dynamic(
        self,
        total: int,
        infantry: int,
        walkers: int,
        support: int,
        *,
        screen_efficiency: float = 0.0,
    ) -> tuple[int, int, int]:
        if total <= 0:
            return (0, 0, 0)

        if screen_efficiency > 0.0 and walkers > 0:
            effective_protection = self.config.walker_screen_infantry_protect * screen_efficiency
            inf_weight = 0.7 * (1.0 - effective_protection)
            walk_weight = 0.2 + 0.7 * effective_protection
            sup_weight = 0.1
        else:
            inf_weight = 0.7
            walk_weight = 0.2
            sup_weight = 0.1

        raw = (total * inf_weight, total * walk_weight, total * sup_weight)
        inf_loss = min(infantry, int(raw[0]))
        walk_loss = min(walkers, int(raw[1]))
        sup_loss = min(support, int(raw[2]))
        remaining = total - (inf_loss + walk_loss + sup_loss)

        for idx in (0, 1, 2):
            if remaining <= 0:
                break
            if idx == 0:
                cap = infantry - inf_loss
                add = min(cap, remaining)
                inf_loss += add
            elif idx == 1:
                cap = walkers - walk_loss
                add = min(cap, remaining)
                walk_loss += add
            else:
                cap = support - sup_loss
                add = min(cap, remaining)
                sup_loss += add
            remaining -= add

        return (inf_loss, walk_loss, sup_loss)

    @staticmethod
    def _calculate_screen_efficiency(walkers: int, infantry: int) -> float:
        if infantry <= 0:
            return 1.0
        capacity = walkers * WALKER_COVERAGE_CAPACITY
        return min(1.0, capacity / max(1, infantry))


def calculate_power(
    infantry: int,
    walkers: int,
    support: int,
    cohesion: float,
    supply_modifier: float = 1.0,
    fortification: float = 1.0,
) -> float:
    base_power = (infantry * 1.0) + (walkers * 5.0) + (support * 0.5)
    return base_power * cohesion * supply_modifier * fortification


def get_supply_modifier(supplies: Supplies, ammo_needed: int, fuel_needed: int) -> float:
    ammo_ratio = min(1.0, supplies.ammo / max(1, ammo_needed))
    fuel_ratio = min(1.0, supplies.fuel / max(1, fuel_needed))
    return max(0.5, (ammo_ratio + fuel_ratio) / 2)


def start_raid_session(state: "GameState", rng: random.Random) -> RaidCombatSession:
    tf = state.task_force
    enemy = state.contested_planet.enemy
    config = state.rules.globals

    supply_mod = get_supply_modifier(tf.supplies, config.raid_ammo_cost, config.raid_fuel_cost)

    ammo_ratio = min(1.0, tf.supplies.ammo / max(1, config.raid_ammo_cost))
    fuel_ratio = min(1.0, tf.supplies.fuel / max(1, config.raid_fuel_cost))

    return RaidCombatSession(
        rng=rng,
        config=config,
        supply_mod=supply_mod,
        enemy_fortification=enemy.fortification,
        supplies_before=tf.supplies,
        your_infantry=tf.composition.infantry,
        your_walkers=tf.composition.walkers,
        your_support=tf.composition.support,
        your_cohesion=max(0.0, min(1.0, tf.readiness)),
        enemy_infantry=enemy.infantry,
        enemy_walkers=enemy.walkers,
        enemy_support=enemy.support,
        enemy_cohesion=max(0.0, min(1.0, enemy.cohesion)),
        ammo_ratio=ammo_ratio,
        fuel_ratio=fuel_ratio,
        intel_confidence=enemy.intel_confidence,
        initial_walkers=tf.composition.walkers,
        max_ticks=config.raid_max_ticks,
    )


def execute_raid(state: "GameState", rng: random.Random) -> CombatResult:
    session = start_raid_session(state, rng)
    while session.outcome is None:
        session.step()
    return session.to_result()

