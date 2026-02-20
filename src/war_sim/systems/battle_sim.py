from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from war_sim.domain.battle_models import BattleDayTick, BattleSideState, BattleSupplySnapshot
from war_sim.domain.ops_models import OperationPhase, Phase1Decisions, Phase2Decisions, Phase3Decisions
from war_sim.domain.types import Supplies
from war_sim.sim.state import GameState


@dataclass(frozen=True)
class BattleDayResult:
    tick: BattleDayTick
    readiness_delta: float
    cohesion_delta: float
    enemy_cohesion_delta: float
    defender_readiness_delta: float
    attacker_collapsed: bool
    defender_collapsed: bool


class BattleSimulator:
    @staticmethod
    def tick_day(
        *,
        state: GameState,
        operation,
        phase: OperationPhase,
        decisions: Phase1Decisions | Phase2Decisions | Phase3Decisions,
        objective_difficulty: float,
        global_day: int,
        day_index: int,
        rng,
        log: Callable[[str, float, str, str], None],
    ) -> BattleDayResult:
        attacker = operation.battle_attacker
        defender = operation.battle_defender
        if attacker is None or defender is None:
            raise RuntimeError("Battle state not initialized")

        attacker.clamp()
        defender.clamp()

        modifiers = _decision_modifiers(state, phase, decisions)
        operation_type = state.rules.operation_types.get(operation.op_type.value)
        supply_scale = operation_type.supply_cost_multiplier if operation_type else 1.0
        intensity = _clamp(modifiers["intensity_mult"], 0.7, 1.4)

        battle_rules = state.rules.battle
        supply_rates = battle_rules.supply_rates

        phase_axis = _decision_value(decisions, "approach_axis", "direct")
        phase_posture = _decision_value(decisions, "engagement_posture", "methodical")
        phase_fire = _decision_value(decisions, "fire_support_prep", "conserve")
        phase_focus = _decision_value(decisions, "exploit_vs_secure", "secure")

        ammo_req = int(
            round(
                (
                    attacker.infantry * supply_rates.ammo_per_infantry_per_intensity
                    + attacker.walkers * supply_rates.ammo_per_walker_per_intensity
                    + attacker.support * supply_rates.ammo_per_support_per_intensity
                )
                * intensity
                * modifiers["ammo_mult"]
                * supply_scale
            )
        )
        fuel_req = int(
            round(
                (
                    attacker.walkers * supply_rates.fuel_per_walker_per_intensity
                    + supply_rates.fuel_axis_extra.get(phase_axis, 1.0)
                )
                * intensity
                * modifiers["fuel_mult"]
                * supply_scale
            )
        )
        med_req_maint = int(
            round(
                attacker.total_units()
                * supply_rates.med_per_unit_per_day
                * modifiers["med_mult"]
                * supply_scale
            )
        )

        front_supplies = state.front_supplies
        ammo_before = front_supplies.ammo
        fuel_before = front_supplies.fuel
        med_before = front_supplies.med_spares

        ammo_ratio = 1.0 if ammo_req <= 0 else min(1.0, ammo_before / max(1, ammo_req))
        fuel_ratio = 1.0 if fuel_req <= 0 else min(1.0, fuel_before / max(1, fuel_req))
        med_ratio = 1.0 if med_req_maint <= 0 else min(1.0, med_before / max(1, med_req_maint))

        attacker_morale = math.sqrt(_clamp(attacker.readiness, 0.0, 1.0) * _clamp(attacker.cohesion, 0.0, 1.0))
        defender_morale = math.sqrt(_clamp(defender.readiness, 0.0, 1.0) * _clamp(defender.cohesion, 0.0, 1.0))

        battlefield = operation.battlefield
        terrain_id = battlefield.terrain_id if battlefield is not None else "default_battleground"
        infrastructure = battlefield.infrastructure if battlefield is not None else 10
        combat_width_multiplier = battlefield.combat_width_multiplier if battlefield is not None else 1.0
        attacker_power_mult = battlefield.attacker_power_mult if battlefield is not None else 1.0
        defender_power_mult = battlefield.defender_power_mult if battlefield is not None else 1.0
        attacker_progress_mult = battlefield.attacker_progress_mult if battlefield is not None else 1.0
        attacker_loss_mult = battlefield.attacker_loss_mult if battlefield is not None else 1.0
        walker_power_mult_attacker = battlefield.walker_power_mult_attacker if battlefield is not None else 1.0
        walker_power_mult_defender = battlefield.walker_power_mult_defender if battlefield is not None else 1.0

        force_limit_battalions = compute_force_limit(infrastructure, combat_width_multiplier)
        engagement_cap_manpower = max(0, force_limit_battalions * battle_rules.manpower_per_battalion)

        attacker_role_manpower = _side_role_manpower(attacker, battle_rules)
        defender_role_manpower = _side_role_manpower(defender, battle_rules)
        attacker_total_manpower = sum(attacker_role_manpower.values())
        defender_total_manpower = sum(defender_role_manpower.values())

        attacker_eligible_manpower = _eligible_manpower(
            total_manpower=attacker_total_manpower,
            morale=attacker_morale,
            rules=battle_rules,
        )
        defender_eligible_manpower = _eligible_manpower(
            total_manpower=defender_total_manpower,
            morale=defender_morale,
            rules=battle_rules,
        )

        attacker_advantage_expansion = _advantage_expansion(
            eligible_side=attacker_eligible_manpower,
            eligible_other=defender_eligible_manpower,
            battle_rules=battle_rules,
            rng=rng,
        )
        defender_advantage_expansion = _advantage_expansion(
            eligible_side=defender_eligible_manpower,
            eligible_other=attacker_eligible_manpower,
            battle_rules=battle_rules,
            rng=rng,
        )

        attacker_engagement_cap = int(engagement_cap_manpower * (1.0 + attacker_advantage_expansion))
        defender_engagement_cap = int(engagement_cap_manpower * (1.0 + defender_advantage_expansion))

        attacker_weights = _role_participation_weights(
            role_manpower=attacker_role_manpower,
            morale=attacker_morale,
            role_stats=battle_rules.attacker_participation_stats,
            eligible_manpower=attacker_eligible_manpower,
        )
        defender_weights = _role_participation_weights(
            role_manpower=defender_role_manpower,
            morale=defender_morale,
            role_stats=battle_rules.defender_participation_stats,
            eligible_manpower=defender_eligible_manpower,
        )

        attacker_engaged_role_manpower = _allocate_engaged_manpower(
            role_manpower=attacker_role_manpower,
            role_weights=attacker_weights,
            engagement_cap=min(attacker_engagement_cap, attacker_eligible_manpower),
        )
        defender_engaged_role_manpower = _allocate_engaged_manpower(
            role_manpower=defender_role_manpower,
            role_weights=defender_weights,
            engagement_cap=min(defender_engagement_cap, defender_eligible_manpower),
        )

        attacker_engaged_manpower = int(round(sum(attacker_engaged_role_manpower.values())))
        defender_engaged_manpower = int(round(sum(defender_engaged_role_manpower.values())))

        attacker_engagement_ratio = attacker_engaged_manpower / max(1.0, attacker_total_manpower)
        defender_engagement_ratio = defender_engaged_manpower / max(1.0, defender_total_manpower)
        attacker_role_engagement_ratio = _role_engagement_ratio(attacker_role_manpower, attacker_engaged_role_manpower)
        defender_role_engagement_ratio = _role_engagement_ratio(defender_role_manpower, defender_engaged_role_manpower)

        role_power = {name: role.base_power for name, role in state.rules.unit_roles.items()}
        infantry_power = role_power.get("infantry", 1.0)
        walker_power = role_power.get("walkers", 12.0)
        support_power = role_power.get("support", 4.0)

        attacker_base_power = (
            attacker.infantry * infantry_power * attacker_role_engagement_ratio["infantry"]
            + attacker.walkers * walker_power * attacker_role_engagement_ratio["walkers"] * walker_power_mult_attacker
            + attacker.support * support_power * attacker_role_engagement_ratio["support"]
        ) * attacker_power_mult
        defender_base_power = (
            defender.infantry * infantry_power * defender_role_engagement_ratio["infantry"]
            + defender.walkers * walker_power * defender_role_engagement_ratio["walkers"] * walker_power_mult_defender
            + defender.support * support_power * defender_role_engagement_ratio["support"]
        ) * defender_power_mult

        supply_power_mod = (0.4 + 0.6 * ammo_ratio) * (0.7 + 0.3 * fuel_ratio) * (0.85 + 0.15 * med_ratio)
        defense_mult = 1.0 + (
            battle_rules.fortification_power_factor * (operation.enemy_fortification_current - 1.0)
        ) + (battle_rules.objective_difficulty_power_factor * (objective_difficulty - 1.0))
        defense_mult = max(0.7, defense_mult)

        your_power = max(
            0.1,
            attacker_base_power * attacker_morale * supply_power_mod * modifiers["progress_mult"],
        )
        enemy_power = max(0.1, defender_base_power * defender_morale * defense_mult)

        support_role = state.rules.unit_roles.get("support")
        recon_cap = 0.0
        if support_role and support_role.recon:
            recon_cap = support_role.recon.get("variance_reduction", 0.0)
        recon_bonus = min(recon_cap, attacker.support * battle_rules.initiative_recon_per_support)

        intel_confidence = state.contested_planet.enemy.intel_confidence
        variance = battle_rules.variance_base * modifiers["variance_mult"]
        variance *= (1.0 - intel_confidence) * (1.0 - recon_bonus)
        variance = _clamp(variance, 0.05, battle_rules.variance_cap)

        initiative_score = battle_rules.initiative_base
        initiative_score += battle_rules.initiative_axis_bonus.get(phase_axis, 0.0)
        initiative_score += modifiers["initiative_bonus"]
        initiative_score += recon_bonus
        initiative_score += rng.uniform(-variance, variance)
        initiative = initiative_score > 0.5

        your_advantage = your_power / max(0.1, enemy_power)
        your_damage = battle_rules.base_damage_rate * intensity * (1.0 / max(0.5, your_advantage))
        enemy_damage = battle_rules.base_damage_rate * intensity * your_advantage
        if initiative:
            enemy_damage *= 1.10
            your_damage *= 0.95
        else:
            your_damage *= 1.05

        your_damage *= rng.uniform(1.0 - variance, 1.0 + variance)
        enemy_damage *= rng.uniform(1.0 - variance, 1.0 + variance)

        your_damage = _clamp(your_damage, 0.0, 0.35)
        enemy_damage = _clamp(enemy_damage, 0.0, 0.35)

        attacker_cohesion_before = attacker.cohesion
        defender_cohesion_before = defender.cohesion

        attacker.cohesion = _clamp(attacker.cohesion - your_damage, 0.0, 1.0)
        defender.cohesion = _clamp(defender.cohesion - enemy_damage, 0.0, 1.0)

        attacker_size_before = attacker.total_units()
        defender_size_before = defender.total_units()

        your_cas_mean = (
            battle_rules.base_casualty_rate
            * intensity
            * your_damage
            * attacker_size_before
            * attacker_engagement_ratio
            * attacker_loss_mult
        )
        enemy_cas_mean = (
            battle_rules.base_casualty_rate
            * intensity
            * enemy_damage
            * defender_size_before
            * defender_engagement_ratio
        )

        your_cas_mean *= max(0.5, 1.0 + modifiers["loss_mod"])

        shortage_flags: list[str] = []
        your_cas_mean = _apply_shortage_effect(
            your_cas_mean,
            "ammo",
            ammo_ratio,
            state,
            shortage_flags,
            log,
        )
        your_cas_mean = _apply_shortage_effect(
            your_cas_mean,
            "fuel",
            fuel_ratio,
            state,
            shortage_flags,
            log,
        )
        your_cas_mean = _apply_shortage_effect(
            your_cas_mean,
            "med_spares",
            med_ratio,
            state,
            shortage_flags,
            log,
        )

        sustainment_reduction = 0.0
        if support_role and support_role.sustainment and attacker.support > 0:
            reduction_cap = support_role.sustainment.get("casualty_reduction", 0.0)
            coverage = min(1.0, attacker.support / max(1.0, attacker.infantry / 25.0))
            sustainment_reduction = reduction_cap * coverage
            your_cas_mean *= max(0.2, 1.0 - sustainment_reduction)

        your_casualties = int(max(0, rng.gauss(your_cas_mean, max(1.0, your_cas_mean * 0.25))))
        enemy_casualties = int(max(0, rng.gauss(enemy_cas_mean, max(1.0, enemy_cas_mean * 0.25))))

        your_casualties = min(attacker_size_before, your_casualties)
        enemy_casualties = min(defender_size_before, enemy_casualties)

        your_losses = _split_losses(your_casualties, attacker)
        screen_transfer = _apply_walker_screen(attacker, your_losses, operation, state)
        if screen_transfer > 0:
            shortage_flags.append("walker_screen")
        enemy_losses = _split_losses(enemy_casualties, defender)

        attacker.infantry -= your_losses["infantry"]
        attacker.walkers -= your_losses["walkers"]
        attacker.support -= your_losses["support"]
        defender.infantry -= enemy_losses["infantry"]
        defender.walkers -= enemy_losses["walkers"]
        defender.support -= enemy_losses["support"]

        attacker.clamp()
        defender.clamp()

        med_req_cas = int(round(sum(your_losses.values()) * supply_rates.med_per_loss * modifiers["med_mult"] * supply_scale))
        med_req = med_req_maint + med_req_cas

        ammo_spent = min(ammo_before, max(0, ammo_req))
        fuel_spent = min(fuel_before, max(0, fuel_req))
        med_spent = min(med_before, max(0, med_req))

        state.set_front_supplies(
            Supplies(
                ammo=ammo_before - ammo_spent,
                fuel=fuel_before - fuel_spent,
                med_spares=med_before - med_spent,
            ).clamp_non_negative()
        )

        if ammo_spent < ammo_req:
            shortage_flags.append("ammo_shortage")
        if fuel_spent < fuel_req:
            shortage_flags.append("fuel_shortage")
        if med_spent < med_req:
            shortage_flags.append("med_shortage")

        progress_base = 1.0 / max(1, operation.estimated_total_days)
        ratio_term = 1.0 / (1.0 + math.exp(-battle_rules.progress_ratio_scale * math.log(max(your_advantage, 0.05))))
        progress_delta = progress_base * ratio_term * modifiers["progress_mult"] * attacker_progress_mult
        progress_delta += modifiers["progress_mod"] * 0.1
        progress_delta += _shortage_progress_penalty(shortage_flags, state, log)

        fort_erosion = battle_rules.fortification_erosion.base_erosion_per_day * modifiers["fort_erosion_mult"]
        if phase == OperationPhase.ENGAGEMENT and phase_posture == "siege":
            fort_erosion *= battle_rules.fortification_erosion.siege_multiplier
        if phase == OperationPhase.CONTACT_SHAPING and phase_fire == "preparatory":
            fort_erosion *= battle_rules.fortification_erosion.preparatory_multiplier
        if initiative and your_advantage >= 1.0:
            operation.enemy_fortification_current = _clamp(
                operation.enemy_fortification_current - fort_erosion,
                0.6,
                2.5,
            )
        elif your_advantage < 0.9:
            operation.enemy_fortification_current = _clamp(
                operation.enemy_fortification_current - battle_rules.fortification_erosion.enemy_counter_erosion,
                0.6,
                2.5,
            )

        if phase == OperationPhase.EXPLOIT_CONSOLIDATE and phase_focus == "secure":
            attacker.readiness = _clamp(
                attacker.readiness + battle_rules.cohesion_model.recovery_per_day_secure,
                0.0,
                1.0,
            )

        casualty_ratio = 0.0
        if attacker_size_before > 0:
            casualty_ratio = sum(your_losses.values()) / attacker_size_before
        readiness_delta = -((0.015 * intensity) + (casualty_ratio * 0.20))

        med_class = state.rules.supply_classes.get("med_spares")
        if med_class and med_spent < med_req:
            readiness_delta += med_class.shortage_effects.get("readiness_degradation", 0.0)

        if phase == OperationPhase.EXPLOIT_CONSOLIDATE and phase_focus == "secure":
            readiness_delta += battle_rules.cohesion_model.recovery_per_day_secure

        attacker.readiness = _clamp(attacker.readiness + readiness_delta, 0.0, 1.0)

        defender_casualty_ratio = 0.0
        if defender_size_before > 0:
            defender_casualty_ratio = sum(enemy_losses.values()) / defender_size_before
        defender_readiness_delta = -((0.015 * intensity) + (defender_casualty_ratio * 0.20))
        defender.readiness = _clamp(defender.readiness + defender_readiness_delta, 0.0, 1.0)

        cohesion_delta = attacker.cohesion - attacker_cohesion_before
        enemy_cohesion_delta = defender.cohesion - defender_cohesion_before

        tags: list[str] = []
        if initiative:
            tags.append("INITIATIVE")
        if screen_transfer > 0:
            tags.append("WALKER_SCREEN")
        if terrain_id == "foundry_industrial_complex":
            tags.append("TERRAIN_FOUNDRY")
        if (attacker_engaged_manpower < attacker_eligible_manpower) or (
            defender_engaged_manpower < defender_eligible_manpower
        ):
            tags.append("WIDTH_LIMITED")
        if attacker_advantage_expansion > 0.0 or defender_advantage_expansion > 0.0:
            tags.append("ADV_EXPANSION")
        tags.extend(sorted(set(shortage_flags)))

        supply_snapshot = BattleSupplySnapshot(
            ammo_before=ammo_before,
            fuel_before=fuel_before,
            med_before=med_before,
            ammo_spent=ammo_spent,
            fuel_spent=fuel_spent,
            med_spent=med_spent,
            ammo_ratio=ammo_ratio,
            fuel_ratio=fuel_ratio,
            med_ratio=med_ratio,
            shortage_flags=sorted(set(shortage_flags)),
        )

        tick = BattleDayTick(
            day_index=day_index,
            global_day=global_day,
            phase=phase.value,
            terrain_id=terrain_id,
            infrastructure=infrastructure,
            combat_width_multiplier=combat_width_multiplier,
            force_limit_battalions=force_limit_battalions,
            engagement_cap_manpower=engagement_cap_manpower,
            attacker_eligible_manpower=int(round(attacker_eligible_manpower)),
            defender_eligible_manpower=int(round(defender_eligible_manpower)),
            attacker_engaged_manpower=attacker_engaged_manpower,
            defender_engaged_manpower=defender_engaged_manpower,
            attacker_engagement_ratio=attacker_engagement_ratio,
            defender_engagement_ratio=defender_engagement_ratio,
            attacker_advantage_expansion=attacker_advantage_expansion,
            defender_advantage_expansion=defender_advantage_expansion,
            your_power=your_power,
            enemy_power=enemy_power,
            your_advantage=your_advantage,
            initiative=initiative,
            progress_delta=progress_delta,
            your_losses=your_losses,
            enemy_losses=enemy_losses,
            your_remaining={
                "infantry": attacker.infantry,
                "walkers": attacker.walkers,
                "support": attacker.support,
            },
            enemy_remaining={
                "infantry": defender.infantry,
                "walkers": defender.walkers,
                "support": defender.support,
            },
            your_cohesion=attacker.cohesion,
            enemy_cohesion=defender.cohesion,
            supplies=supply_snapshot,
            tags=tags,
        )

        log("intensity", intensity, "combat", "Engagement intensity from selected decisions")
        log("your_power", your_power, "combat", "Attacker effective power")
        log("enemy_power", enemy_power, "combat", "Defender effective power")
        log("force_limit_battalions", float(force_limit_battalions), "combat", "Terrain-constrained force limit")
        log("engagement_cap_manpower", float(engagement_cap_manpower), "combat", "Base engagement cap")
        log("attacker_engagement_ratio", attacker_engagement_ratio, "combat", "Attacker engaged manpower share")
        log("defender_engagement_ratio", defender_engagement_ratio, "combat", "Defender engaged manpower share")
        log("terrain_attacker_power_mult", attacker_power_mult, "combat", "Terrain attacker power modifier")
        log("terrain_defender_power_mult", defender_power_mult, "combat", "Terrain defender power modifier")
        log("terrain_attacker_progress_mult", attacker_progress_mult, "progress", "Terrain attacker progress modifier")
        log("terrain_attacker_loss_mult", attacker_loss_mult, "casualties", "Terrain attacker casualty pressure")
        log("decision_loss_mod", modifiers["loss_mod"], "casualties", "Decision-driven casualty modifier")
        log("advantage", your_advantage, "progress", "Power ratio advantage")
        log("progress", progress_delta, "progress", "Daily progress contribution")
        log("readiness", readiness_delta, "readiness", "Daily readiness change")
        log("defender_readiness", defender_readiness_delta, "readiness", "Daily defender readiness change")
        log("cohesion", cohesion_delta, "cohesion", "Daily attacker cohesion change")
        log("enemy_cohesion", enemy_cohesion_delta, "enemy_cohesion", "Daily defender cohesion change")

        attacker_collapsed = attacker.total_units() <= 0 or attacker.cohesion <= 0.0
        defender_collapsed = defender.total_units() <= 0 or defender.cohesion <= 0.0

        return BattleDayResult(
            tick=tick,
            readiness_delta=readiness_delta,
            cohesion_delta=cohesion_delta,
            enemy_cohesion_delta=enemy_cohesion_delta,
            defender_readiness_delta=defender_readiness_delta,
            attacker_collapsed=attacker_collapsed,
            defender_collapsed=defender_collapsed,
        )


def compute_force_limit(infrastructure: int, combat_width_multiplier: float) -> int:
    return int(math.ceil((5.0 + infrastructure / 2.0) * combat_width_multiplier))


def _decision_value(decisions, key: str, default: str) -> str:
    return str(getattr(decisions, key, default))


def _side_role_manpower(side: BattleSideState, battle_rules) -> dict[str, float]:
    return {
        "infantry": max(0.0, float(side.infantry)),
        "walkers": max(0.0, float(side.walkers) * battle_rules.manpower_per_walker),
        "support": max(0.0, float(side.support) * battle_rules.manpower_per_support),
    }


def _eligible_manpower(*, total_manpower: float, morale: float, rules) -> float:
    if morale < rules.eligibility_min_morale:
        return 0.0
    if total_manpower < rules.eligibility_min_manpower:
        return 0.0
    return max(0.0, total_manpower)


def _advantage_expansion(*, eligible_side: float, eligible_other: float, battle_rules, rng) -> float:
    if eligible_side <= 0.0:
        return 0.0
    ratio = eligible_side / max(1.0, eligible_other)
    expansion_base = max(0.0, (ratio - 1.0) * battle_rules.numeric_advantage_expansion_scale)
    jitter = rng.uniform(0.0, battle_rules.numeric_advantage_expansion_random_max)
    return min(battle_rules.numeric_advantage_expansion_cap, expansion_base + jitter)


def _role_participation_weights(
    *,
    role_manpower: dict[str, float],
    morale: float,
    role_stats: dict[str, float],
    eligible_manpower: float,
) -> dict[str, float]:
    if eligible_manpower <= 0.0:
        return {key: 0.0 for key in role_manpower.keys()}
    return {
        key: max(0.0, role_manpower[key] * morale * 1.0 * role_stats.get(key, 1.0))
        for key in role_manpower.keys()
    }


def _allocate_engaged_manpower(
    *,
    role_manpower: dict[str, float],
    role_weights: dict[str, float],
    engagement_cap: float,
) -> dict[str, float]:
    allocation = {key: 0.0 for key in role_manpower.keys()}
    if engagement_cap <= 0.0:
        return allocation
    total_weight = sum(max(0.0, weight) for weight in role_weights.values())
    if total_weight <= 0.0:
        return allocation

    for role, weight in role_weights.items():
        share = engagement_cap * max(0.0, weight) / total_weight
        allocation[role] = min(role_manpower.get(role, 0.0), share)

    remaining = max(0.0, engagement_cap - sum(allocation.values()))
    if remaining <= 0.0:
        return allocation

    candidates = [role for role in allocation.keys() if role_manpower.get(role, 0.0) > allocation[role]]
    while remaining > 0.5 and candidates:
        candidate_weight_sum = sum(max(0.0, role_weights.get(role, 0.0)) for role in candidates)
        if candidate_weight_sum <= 0.0:
            break
        spent = 0.0
        for role in list(candidates):
            proportional = remaining * max(0.0, role_weights.get(role, 0.0)) / candidate_weight_sum
            room = max(0.0, role_manpower.get(role, 0.0) - allocation[role])
            grant = min(room, proportional)
            allocation[role] += grant
            spent += grant
        if spent <= 0.0:
            break
        remaining = max(0.0, remaining - spent)
        candidates = [role for role in allocation.keys() if role_manpower.get(role, 0.0) > allocation[role]]
    return allocation


def _role_engagement_ratio(
    role_manpower: dict[str, float],
    engaged_role_manpower: dict[str, float],
) -> dict[str, float]:
    ratios: dict[str, float] = {}
    for role, total in role_manpower.items():
        ratios[role] = _clamp(engaged_role_manpower.get(role, 0.0) / max(1.0, total), 0.0, 1.0)
    return ratios


def _decision_modifiers(
    state: GameState,
    phase: OperationPhase,
    decisions: Phase1Decisions | Phase2Decisions | Phase3Decisions,
) -> dict[str, float]:
    combined = {
        "progress_mod": 0.0,
        "loss_mod": 0.0,
        "intensity_mult": 1.0,
        "variance_mult": 1.0,
        "initiative_bonus": 0.0,
        "progress_mult": 1.0,
        "ammo_mult": 1.0,
        "fuel_mult": 1.0,
        "med_mult": 1.0,
        "fort_erosion_mult": 1.0,
    }

    entries: list[dict[str, float]] = []
    if phase == OperationPhase.CONTACT_SHAPING and isinstance(decisions, Phase1Decisions):
        entries.append(state.rules.approach_axes.get(decisions.approach_axis, {}))
        entries.append(state.rules.fire_support_prep.get(decisions.fire_support_prep, {}))
    elif phase == OperationPhase.ENGAGEMENT and isinstance(decisions, Phase2Decisions):
        entries.append(state.rules.engagement_postures.get(decisions.engagement_posture, {}))
        entries.append(state.rules.risk_tolerances.get(decisions.risk_tolerance, {}))
    elif phase == OperationPhase.EXPLOIT_CONSOLIDATE and isinstance(decisions, Phase3Decisions):
        entries.append(state.rules.exploit_vs_secure.get(decisions.exploit_vs_secure, {}))

    for entry in entries:
        for key in ("progress_mod", "loss_mod", "initiative_bonus"):
            combined[key] += float(entry.get(key, 0.0))
        for key in (
            "intensity_mult",
            "variance_mult",
            "progress_mult",
            "ammo_mult",
            "fuel_mult",
            "med_mult",
            "fort_erosion_mult",
        ):
            combined[key] *= float(entry.get(key, 1.0))
    return combined


def _apply_shortage_effect(
    base_casualty_mean: float,
    supply_id: str,
    ratio: float,
    state: GameState,
    shortage_flags: list[str],
    log: Callable[[str, float, str, str], None],
) -> float:
    if ratio >= 1.0:
        return base_casualty_mean
    supply_class = state.rules.supply_classes.get(supply_id)
    if supply_class is None:
        return base_casualty_mean
    multiplier = supply_class.shortage_effects.get("loss_multiplier", 1.0)
    shortage_flags.append(f"{supply_id}_pinch")
    log(
        f"{supply_id}_loss_multiplier",
        multiplier,
        "casualties",
        f"{supply_id} shortage increased casualty pressure",
    )
    return base_casualty_mean * multiplier


def _shortage_progress_penalty(
    shortage_flags: list[str],
    state: GameState,
    log: Callable[[str, float, str, str], None],
) -> float:
    penalty = 0.0
    for supply_id in ("ammo", "fuel", "med_spares"):
        if f"{supply_id}_shortage" not in shortage_flags:
            continue
        supply_class = state.rules.supply_classes.get(supply_id)
        if supply_class is None:
            continue
        supply_penalty = supply_class.shortage_effects.get("progress_penalty", 0.0) * 0.1
        penalty += supply_penalty
        log(
            f"{supply_id}_progress_penalty",
            supply_penalty,
            "progress",
            f"{supply_id} shortage slowed operation tempo",
        )
    return penalty


def _split_losses(total: int, side: BattleSideState) -> dict[str, int]:
    if total <= 0:
        return {"infantry": 0, "walkers": 0, "support": 0}

    infantry_loss = min(side.infantry, int(total * 0.7))
    walker_loss = min(side.walkers, int(total * 0.2))
    support_loss = min(side.support, total - infantry_loss - walker_loss)
    remaining = total - infantry_loss - walker_loss - support_loss

    if remaining > 0:
        spare_infantry = max(0, side.infantry - infantry_loss)
        add = min(spare_infantry, remaining)
        infantry_loss += add
        remaining -= add
    if remaining > 0:
        spare_walkers = max(0, side.walkers - walker_loss)
        add = min(spare_walkers, remaining)
        walker_loss += add
        remaining -= add
    if remaining > 0:
        spare_support = max(0, side.support - support_loss)
        add = min(spare_support, remaining)
        support_loss += add

    return {
        "infantry": infantry_loss,
        "walkers": walker_loss,
        "support": support_loss,
    }


def _apply_walker_screen(side: BattleSideState, losses: dict[str, int], operation, state: GameState) -> int:
    if side.walkers <= 0 or losses["infantry"] <= 0:
        return 0

    walker_cfg = state.rules.battle.walker_screen
    infantry = max(1, side.infantry)
    coverage = min(1.0, (side.walkers * walker_cfg.coverage_per_walker) / infantry)
    transfer = int(round(losses["infantry"] * walker_cfg.transfer_fraction_cap * coverage))

    walker_floor = int(max(0, operation.battle_attacker.walkers) * walker_cfg.degradation_threshold)
    walker_absorption_cap = max(0, side.walkers - walker_floor)
    transfer = min(transfer, walker_absorption_cap)

    if transfer <= 0:
        return 0

    losses["infantry"] -= transfer
    losses["walkers"] += transfer
    return transfer


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))
