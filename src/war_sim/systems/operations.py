from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable

from war_sim.domain.events import FactorEvent, FactorScope
from war_sim.domain.ops_models import (
    ActiveOperation,
    OperationIntent,
    OperationPhase,
    OperationPhaseRecord,
    OperationPlan,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
    PhaseSummary,
)
from war_sim.domain.reports import AfterActionReport, TopFactor
from war_sim.domain.types import LocationId, ObjectiveStatus, Supplies
from war_sim.sim.state import GameState
from war_sim.systems.combat import calculate_power


@dataclass()
class PhaseResolution:
    progress_delta: float
    losses: int
    supplies_spent: Supplies
    readiness_delta: float = 0.0


class FactorLog:
    def __init__(self, scope: FactorScope):
        self.scope = scope
        self.events: list[FactorEvent] = []

    def add(self, name: str, value: float, delta: str, why: str, phase: OperationPhase) -> None:
        self.events.append(
            FactorEvent(
                name=name,
                value=value,
                delta=delta,
                why=why,
                phase=phase.value,
                scope=self.scope,
            )
        )


def start_operation(state: GameState, plan: OperationPlan, rng) -> None:
    intent = plan.to_intent()
    start_operation_phased(state, intent, rng)
    if state.operation is None:
        raise RuntimeError("Operation failed to start")
    state.operation.decisions.phase1 = plan.to_phase1()
    state.operation.decisions.phase2 = plan.to_phase2()
    state.operation.decisions.phase3 = plan.to_phase3()
    state.operation.awaiting_player_decision = False
    state.operation.auto_advance = True


def start_operation_phased(state: GameState, intent: OperationIntent, rng) -> None:
    if state.operation is not None or state.raid_session is not None:
        raise RuntimeError("Only one active operation allowed")

    op_config = state.rules.operation_types.get(intent.op_type.value)
    if op_config is None:
        base_days = 3
        duration_range = (2, 5)
    else:
        base_days = op_config.base_duration_days
        duration_range = op_config.duration_range

    fort_mod = max(0, int((state.contested_planet.enemy.fortification - 1.0) * 2))
    control_mod = max(0, int((1.0 - state.contested_planet.control) * 2))
    estimated_days = base_days + fort_mod + control_mod
    estimated_days = max(duration_range[0], min(estimated_days, duration_range[1]))

    phase_durations = _calculate_phase_durations(intent.op_type, estimated_days)

    enemy = state.contested_planet.enemy
    tf = state.task_force
    enemy_power = calculate_power(
        enemy.infantry,
        enemy.walkers,
        enemy.support,
        cohesion=max(0.0, min(1.0, enemy.cohesion)),
    )
    your_power = calculate_power(
        tf.composition.infantry,
        tf.composition.walkers,
        tf.composition.support,
        cohesion=max(0.0, min(1.0, tf.readiness)),
    )
    raw_ratio = enemy_power / max(1.0, your_power)
    uncertainty = (1.0 - enemy.intel_confidence) * 0.25
    sampled_strength = raw_ratio + rng.uniform(-uncertainty, uncertainty)
    sampled_strength = max(0.5, min(2.0, sampled_strength))

    state.operation = ActiveOperation(
        intent=intent,
        estimated_total_days=estimated_days,
        phase_durations=phase_durations,
        phase_start_day=state.day,
        sampled_enemy_strength=sampled_strength,
        op_id=str(uuid.uuid4()),
    )


def submit_phase_decisions(
    state: GameState, decisions: Phase1Decisions | Phase2Decisions | Phase3Decisions
) -> None:
    if state.operation is None:
        raise RuntimeError("No active operation")
    if not state.operation.awaiting_player_decision:
        raise RuntimeError("Not awaiting player decision")

    op = state.operation
    if op.current_phase == OperationPhase.CONTACT_SHAPING:
        if not isinstance(decisions, Phase1Decisions):
            raise TypeError("Expected Phase1Decisions for Contact/Shaping phase")
        op.decisions.phase1 = decisions
    elif op.current_phase == OperationPhase.ENGAGEMENT:
        if not isinstance(decisions, Phase2Decisions):
            raise TypeError("Expected Phase2Decisions for Engagement phase")
        op.decisions.phase2 = decisions
    elif op.current_phase == OperationPhase.EXPLOIT_CONSOLIDATE:
        if not isinstance(decisions, Phase3Decisions):
            raise TypeError("Expected Phase3Decisions for Exploit/Consolidate phase")
        op.decisions.phase3 = decisions
    else:
        raise RuntimeError(f"Cannot submit decisions for phase {op.current_phase}")

    op.awaiting_player_decision = False
    op.phase_start_day = state.day


def acknowledge_phase_result(state: GameState) -> OperationPhaseRecord | None:
    if state.operation is None:
        return None
    record = state.operation.pending_phase_record
    if record is None:
        return None

    state.operation.pending_phase_record = None
    state.operation.advance_phase()

    if state.operation.current_phase == OperationPhase.COMPLETE:
        _finalize_operation(state)

    return record


def progress_if_applicable(state: GameState, rng, factor_log: FactorLog) -> None:
    if state.operation is not None and not state.operation.awaiting_player_decision:
        state.operation.day_in_operation += 1
        state.operation.day_in_phase += 1

        if state.operation.is_phase_complete():
            _resolve_current_phase(state, factor_log)

            if (
                state.operation is not None
                and state.operation.decisions.is_complete()
                and state.operation.auto_advance
            ):
                acknowledge_phase_result(state)
                if state.operation is not None:
                    state.operation.awaiting_player_decision = False


def _calculate_phase_durations(
    op_type: OperationTypeId, total_days: int
) -> dict[OperationPhase, int]:
    if op_type == OperationTypeId.RAID:
        return {
            OperationPhase.CONTACT_SHAPING: max(1, total_days // 2),
            OperationPhase.ENGAGEMENT: max(0, total_days - total_days // 2),
            OperationPhase.EXPLOIT_CONSOLIDATE: 0,
        }
    elif op_type == OperationTypeId.SIEGE:
        p1 = max(1, total_days // 3)
        p2 = max(1, total_days // 2)
        p3 = max(1, total_days - p1 - p2)
        return {
            OperationPhase.CONTACT_SHAPING: p1,
            OperationPhase.ENGAGEMENT: p2,
            OperationPhase.EXPLOIT_CONSOLIDATE: p3,
        }
    else:
        p1 = max(1, total_days // 3)
        p2 = max(1, total_days // 3)
        p3 = max(1, total_days - p1 - p2)
        return {
            OperationPhase.CONTACT_SHAPING: p1,
            OperationPhase.ENGAGEMENT: p2,
            OperationPhase.EXPLOIT_CONSOLIDATE: p3,
        }


def _operation_supply_multiplier(state: GameState, op: ActiveOperation) -> float:
    op_config = state.rules.operation_types.get(op.op_type.value)
    if op_config is None:
        return 1.0
    return op_config.supply_cost_multiplier


def _resolve_current_phase(state: GameState, factor_log: FactorLog) -> None:
    if state.operation is None:
        return

    op = state.operation
    phase = op.current_phase
    events: list[FactorEvent] = []

    def log(name: str, value: float, delta: str, why: str) -> None:
        factor_log.add(name, value, delta, why, phase)
        events.append(factor_log.events[-1])

    resolution = PhaseResolution(0.0, 0, Supplies(ammo=0, fuel=0, med_spares=0))

    if phase == OperationPhase.CONTACT_SHAPING:
        resolution = _resolve_phase1(state, op, log)
    elif phase == OperationPhase.ENGAGEMENT:
        resolution = _resolve_phase2(state, op, log)
    elif phase == OperationPhase.EXPLOIT_CONSOLIDATE:
        resolution = _resolve_phase3(state, op, log)

    _set_front_supplies(
        state,
        Supplies(
            ammo=max(0, state.front_supplies.ammo - resolution.supplies_spent.ammo),
            fuel=max(0, state.front_supplies.fuel - resolution.supplies_spent.fuel),
            med_spares=max(0, state.front_supplies.med_spares - resolution.supplies_spent.med_spares),
        ),
    )

    _apply_losses(state, resolution.losses)

    op.accumulated_progress += resolution.progress_delta
    op.accumulated_losses += resolution.losses

    state.task_force.readiness = min(
        1.0, max(0.0, state.task_force.readiness + resolution.readiness_delta)
    )

    summary = PhaseSummary(
        progress_delta=resolution.progress_delta,
        losses=resolution.losses,
        supplies_spent=resolution.supplies_spent,
        readiness_delta=resolution.readiness_delta,
    )

    if phase == OperationPhase.CONTACT_SHAPING:
        decisions = op.decisions.phase1
    elif phase == OperationPhase.ENGAGEMENT:
        decisions = op.decisions.phase2
    else:
        decisions = op.decisions.phase3

    record = OperationPhaseRecord(
        phase=phase,
        start_day=op.phase_start_day,
        end_day=state.day,
        decisions=decisions,
        summary=summary,
        events=events,
    )

    op.phase_history.append(record)
    op.pending_phase_record = record
    op.awaiting_player_decision = True


def _resolve_phase1(
    state: GameState, op: ActiveOperation, log: Callable[[str, float, str, str], None]
) -> PhaseResolution:
    d = op.decisions.phase1
    if d is None:
        return PhaseResolution(0.0, 0, Supplies(0, 0, 0))

    phase_days = op.phase_durations.get(OperationPhase.CONTACT_SHAPING, 1)

    approach_rules = state.rules.approach_axes.get(
        d.approach_axis, {"progress_mod": 0.0, "loss_mod": 0.0}
    )
    prep_rules = state.rules.fire_support_prep.get(
        d.fire_support_prep, {"progress_mod": 0.0, "loss_mod": 0.0}
    )

    base_progress = _phase_base_progress(op, OperationPhase.CONTACT_SHAPING, phase_days)
    progress = (
        base_progress
        + approach_rules.get("progress_mod", 0.0)
        + prep_rules.get("progress_mod", 0.0)
    )
    loss_mod = approach_rules.get("loss_mod", 0.0) + prep_rules.get("loss_mod", 0.0)

    log("base_progress", base_progress, "progress", "Base progress from contact & shaping tempo")
    log(
        f"approach_{d.approach_axis}",
        approach_rules.get("progress_mod", 0.0),
        "progress",
        f"Approach: {d.approach_axis}",
    )
    log(
        f"fire_support_{d.fire_support_prep}",
        prep_rules.get("progress_mod", 0.0),
        "progress",
        f"Fire support: {d.fire_support_prep}",
    )

    strength_penalty = -0.10 * ((op.sampled_enemy_strength or 1.0) - 1.0)
    control_penalty = -0.08 * (1.0 - state.contested_planet.control)
    progress += strength_penalty + control_penalty

    log("enemy_strength", strength_penalty, "progress", f"Enemy strength {(op.sampled_enemy_strength or 1.0):.2f}")
    log("planet_control", control_penalty, "progress", f"Control level {state.contested_planet.control:.2f}")

    base_ammo = 15 + (5 if d.fire_support_prep == "preparatory" else 0)
    base_fuel = 10 + (5 if d.approach_axis == "flank" else 0)
    supply_mult = _operation_supply_multiplier(state, op)
    ammo_cost = int(round(base_ammo * phase_days * supply_mult))
    fuel_cost = int(round(base_fuel * phase_days * supply_mult))

    if state.front_supplies.ammo < ammo_cost:
        ammo_class = state.rules.supply_classes.get("ammo")
        if ammo_class:
            penalty = ammo_class.shortage_effects.get("progress_penalty", -0.30)
            progress += penalty
            log("ammo_shortage", penalty, "progress", "Insufficient ammo reduces shaping effectiveness")

    supplies_spent = Supplies(ammo=ammo_cost, fuel=fuel_cost, med_spares=0)

    total_units = (
        state.task_force.composition.infantry
        + state.task_force.composition.walkers
        + state.task_force.composition.support
    )
    losses = int(max(0, (0.03 + loss_mod) * total_units * phase_days))

    return PhaseResolution(progress, losses, supplies_spent)


def _resolve_phase2(
    state: GameState, op: ActiveOperation, log: Callable[[str, float, str, str], None]
) -> PhaseResolution:
    d = op.decisions.phase2
    if d is None:
        return PhaseResolution(0.0, 0, Supplies(0, 0, 0))

    phase_days = op.phase_durations.get(OperationPhase.ENGAGEMENT, 1)

    posture_rules = state.rules.engagement_postures.get(
        d.engagement_posture, {"progress_mod": 0.0, "loss_mod": 0.0}
    )
    risk_rules = state.rules.risk_tolerances.get(
        d.risk_tolerance, {"progress_mod": 0.0, "loss_mod": 0.0, "variance_mod": 0.0}
    )

    base_progress = _phase_base_progress(op, OperationPhase.ENGAGEMENT, phase_days)
    progress = base_progress + posture_rules.get("progress_mod", 0.0) + risk_rules.get(
        "progress_mod", 0.0
    )
    loss_mod = posture_rules.get("loss_mod", 0.0) + risk_rules.get("loss_mod", 0.0)

    log("base_progress", base_progress, "progress", "Base progress from engagement tempo")
    log(
        f"posture_{d.engagement_posture}",
        posture_rules.get("progress_mod", 0.0),
        "progress",
        f"Posture: {d.engagement_posture}",
    )
    log(
        f"risk_{d.risk_tolerance}",
        risk_rules.get("progress_mod", 0.0),
        "progress",
        f"Risk tolerance: {d.risk_tolerance}",
    )

    strength_penalty = -0.15 * ((op.sampled_enemy_strength or 1.0) - 1.0)
    progress += strength_penalty
    log("enemy_strength", strength_penalty, "progress", f"Enemy strength {(op.sampled_enemy_strength or 1.0):.2f}")

    base_ammo = 20 + (10 if d.engagement_posture in ("shock", "siege") else 0)
    base_fuel = 15 + (5 if d.engagement_posture == "siege" else 0)
    supply_mult = _operation_supply_multiplier(state, op)
    ammo_cost = int(round(base_ammo * phase_days * supply_mult))
    fuel_cost = int(round(base_fuel * phase_days * supply_mult))
    med_cost = int(round(4 * phase_days * supply_mult))

    if state.front_supplies.ammo < ammo_cost:
        ammo_class = state.rules.supply_classes.get("ammo")
        if ammo_class:
            penalty = ammo_class.shortage_effects.get("progress_penalty", -0.30)
            progress += penalty
            log("ammo_shortage", penalty, "progress", "Insufficient ammo reduces engagement effectiveness")

    if state.front_supplies.fuel < fuel_cost:
        fuel_class = state.rules.supply_classes.get("fuel")
        if fuel_class:
            penalty = fuel_class.shortage_effects.get("progress_penalty", -0.20)
            progress += penalty
            log("fuel_shortage", penalty, "progress", "Insufficient fuel reduces maneuver ability")

    supplies_spent = Supplies(ammo=ammo_cost, fuel=fuel_cost, med_spares=med_cost)

    total_units = (
        state.task_force.composition.infantry
        + state.task_force.composition.walkers
        + state.task_force.composition.support
    )
    losses = int(max(0, (0.05 + loss_mod) * total_units * phase_days))

    return PhaseResolution(progress, losses, supplies_spent)


def _resolve_phase3(
    state: GameState, op: ActiveOperation, log: Callable[[str, float, str, str], None]
) -> PhaseResolution:
    d = op.decisions.phase3
    if d is None:
        return PhaseResolution(0.0, 0, Supplies(0, 0, 0))

    phase_days = op.phase_durations.get(OperationPhase.EXPLOIT_CONSOLIDATE, 1)

    focus_rules = state.rules.exploit_vs_secure.get(
        d.exploit_vs_secure, {"progress_mod": 0.0, "loss_mod": 0.0}
    )
    end_rules = state.rules.end_states.get(
        d.end_state, {"progress_mod": 0.0, "loss_mod": 0.0, "readiness_delta": 0.0}
    )

    base_progress = _phase_base_progress(op, OperationPhase.EXPLOIT_CONSOLIDATE, phase_days)
    progress = base_progress + focus_rules.get("progress_mod", 0.0) + end_rules.get(
        "progress_mod", 0.0
    )
    loss_mod = focus_rules.get("loss_mod", 0.0) + end_rules.get("loss_mod", 0.0)

    log("base_progress", base_progress, "progress", "Base progress from exploit tempo")
    log(
        f"focus_{d.exploit_vs_secure}",
        focus_rules.get("progress_mod", 0.0),
        "progress",
        f"Exploit vs secure: {d.exploit_vs_secure}",
    )
    log(
        f"end_state_{d.end_state}",
        end_rules.get("progress_mod", 0.0),
        "progress",
        f"End state: {d.end_state}",
    )

    base_ammo = 10
    base_fuel = 12 + (5 if d.exploit_vs_secure == "push" else 0)
    supply_mult = _operation_supply_multiplier(state, op)
    ammo_cost = int(round(base_ammo * phase_days * supply_mult))
    fuel_cost = int(round(base_fuel * phase_days * supply_mult))
    med_cost = int(round(3 * phase_days * supply_mult))

    if state.front_supplies.med_spares < med_cost:
        med_class = state.rules.supply_classes.get("med_spares")
        if med_class:
            penalty = med_class.shortage_effects.get("progress_penalty", -0.15)
            progress += penalty
            log("med_shortage", penalty, "progress", "Insufficient medical supplies reduce sustainment")

    supplies_spent = Supplies(ammo=ammo_cost, fuel=fuel_cost, med_spares=med_cost)

    total_units = (
        state.task_force.composition.infantry
        + state.task_force.composition.walkers
        + state.task_force.composition.support
    )
    support_role = state.rules.unit_roles.get("support")
    medic_reduction = 0.0
    if support_role and support_role.sustainment:
        medic_reduction = min(0.02, 0.002 * state.task_force.composition.support)

    losses_rate = 0.03 + loss_mod - medic_reduction
    losses = int(max(0, losses_rate * total_units * phase_days))

    readiness_delta = float(end_rules.get("readiness_delta", 0.0))
    return PhaseResolution(progress, losses, supplies_spent, readiness_delta)


def _apply_losses(state: GameState, losses: int) -> None:
    if losses <= 0:
        return

    total_units = (
        state.task_force.composition.infantry
        + state.task_force.composition.walkers
        + state.task_force.composition.support
    )
    if total_units == 0:
        return

    losses = min(losses, total_units)

    infantry = state.task_force.composition.infantry
    walkers = state.task_force.composition.walkers
    support = state.task_force.composition.support

    infantry_losses = min(infantry, int(losses * 0.6))
    walker_losses = min(walkers, int(losses * 0.3))
    support_losses = min(support, int(losses * 0.1))
    remaining = losses - (infantry_losses + walker_losses + support_losses)

    if remaining > 0:
        add = min(infantry - infantry_losses, remaining)
        infantry_losses += add
        remaining -= add
    if remaining > 0:
        add = min(walkers - walker_losses, remaining)
        walker_losses += add
        remaining -= add
    if remaining > 0:
        add = min(support - support_losses, remaining)
        support_losses += add
        remaining -= add

    state.task_force.composition.infantry = max(0, infantry - infantry_losses)
    state.task_force.composition.walkers = max(0, walkers - walker_losses)
    state.task_force.composition.support = max(0, support - support_losses)

    if losses > total_units * 0.1:
        state.task_force.readiness = max(0.5, state.task_force.readiness - 0.1)


def _phase_base_progress(op: ActiveOperation, phase: OperationPhase, phase_days: int) -> float:
    if phase_days <= 0 or op.estimated_total_days <= 0:
        return 0.0
    return phase_days / op.estimated_total_days


def _finalize_operation(state: GameState) -> None:
    if state.operation is None:
        return

    op = state.operation
    d3 = op.decisions.phase3

    all_events: list[FactorEvent] = []
    for record in op.phase_history:
        all_events.extend(record.events)

    end_state = d3.end_state if d3 else "withdraw"
    end_state_rules = state.rules.end_states.get(
        end_state,
        {"required_progress": 0.75, "fortification_reduction": 0.0, "reinforcement_reduction": 0.0},
    )
    required_progress = end_state_rules.get("required_progress", 0.75)
    success = op.accumulated_progress >= required_progress

    outcome_map = {
        "capture": "CAPTURED",
        "raid": "RAIDED",
        "destroy": "DESTROYED",
        "withdraw": "WITHDREW",
    }
    if end_state == "withdraw":
        outcome = outcome_map["withdraw"]
        success = False
    else:
        outcome = outcome_map.get(end_state, "FAILED") if success else "FAILED"

    if success:
        fort_reduction = end_state_rules.get("fortification_reduction", 0.0)
        reinf_reduction = end_state_rules.get("reinforcement_reduction", 0.0)
        if end_state == "capture":
            _set_objective(state, op.target, ObjectiveStatus.SECURED)
            state.contested_planet.control = min(1.0, state.contested_planet.control + 0.15)
            state.contested_planet.enemy.fortification = max(
                0.6, state.contested_planet.enemy.fortification - fort_reduction
            )
            state.contested_planet.enemy.reinforcement_rate = max(
                0.0, state.contested_planet.enemy.reinforcement_rate - reinf_reduction
            )
        elif end_state == "raid":
            state.contested_planet.control = min(1.0, state.contested_planet.control + 0.05)
            state.contested_planet.enemy.reinforcement_rate = max(
                0.0, state.contested_planet.enemy.reinforcement_rate - reinf_reduction
            )
        elif end_state == "destroy":
            state.contested_planet.control = min(1.0, state.contested_planet.control + 0.10)
            state.contested_planet.enemy.fortification = max(
                0.6, state.contested_planet.enemy.fortification - fort_reduction
            )
            state.contested_planet.enemy.reinforcement_rate = max(
                0.0, state.contested_planet.enemy.reinforcement_rate - reinf_reduction
            )
    elif end_state != "withdraw":
        state.contested_planet.control = max(0.0, state.contested_planet.control - 0.10)
        state.contested_planet.enemy.fortification = min(
            2.5, state.contested_planet.enemy.fortification + 0.10
        )

    _update_intel_confidence(state, op, success)

    top = _top_factors(all_events)
    state.last_aar = AfterActionReport(
        outcome=outcome,
        target=op.target,
        operation_type=op.op_type.value,
        days=op.day_in_operation,
        losses=op.accumulated_losses,
        remaining_supplies=state.front_supplies,
        top_factors=top,
        phases=list(op.phase_history),
        events=all_events,
    )
    state.operation = None


def _top_factors(events: list[FactorEvent]) -> list[TopFactor]:
    scored: list[tuple[float, FactorEvent]] = []
    for ev in events:
        scored.append((abs(ev.value), ev))
    scored.sort(key=lambda t: t[0], reverse=True)
    top: list[TopFactor] = []
    for _, ev in scored[:5]:
        top.append(TopFactor(name=ev.name, value=ev.value, delta=ev.delta, why=ev.why))
    return top


def _update_intel_confidence(state: GameState, op: ActiveOperation, success: bool) -> None:
    enemy = state.contested_planet.enemy
    gain = 0.02
    if op.decisions.phase1:
        axis = op.decisions.phase1.approach_axis
        if axis == "stealth":
            gain += 0.03
        elif axis == "dispersed":
            gain += 0.02
    support_role = state.rules.unit_roles.get("support")
    if support_role and support_role.recon:
        recon_gain = min(0.05, state.task_force.composition.support * 0.005)
        gain += recon_gain
    if success:
        gain += 0.02
    enemy.intel_confidence = min(0.95, max(0.05, enemy.intel_confidence + gain))


def _get_objective_status(state: GameState, target: OperationTarget) -> ObjectiveStatus:
    if target == OperationTarget.FOUNDRY:
        return state.contested_planet.objectives.foundry
    elif target == OperationTarget.COMMS:
        return state.contested_planet.objectives.comms
    else:
        return state.contested_planet.objectives.power


def _set_objective(state: GameState, target: OperationTarget, status: ObjectiveStatus) -> None:
    if target == OperationTarget.FOUNDRY:
        state.contested_planet.objectives.foundry = status
    elif target == OperationTarget.COMMS:
        state.contested_planet.objectives.comms = status
    elif target == OperationTarget.POWER:
        state.contested_planet.objectives.power = status


def _set_front_supplies(state: GameState, supplies: Supplies) -> None:
    state.logistics.depot_stocks[LocationId.CONTESTED_FRONT] = supplies
    state.task_force.supplies = supplies
