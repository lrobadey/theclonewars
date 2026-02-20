from __future__ import annotations

import uuid
from dataclasses import dataclass

from war_sim.domain.battle_models import BattlePhaseAccumulator, BattleSideState
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
from war_sim.domain.types import ObjectiveStatus, Supplies
from war_sim.sim.state import GameState
from war_sim.systems.battle_sim import BattleSimulator


@dataclass()
class FactorLog:
    scope: FactorScope
    events: list[FactorEvent] = None

    def __post_init__(self) -> None:
        if self.events is None:
            self.events = []

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
    if state.operation is not None:
        raise RuntimeError("Only one active operation allowed")
    if _get_objective_status(state, intent.target) == ObjectiveStatus.SECURED:
        raise RuntimeError(f"Cannot operate against {intent.target.value}; objective already secured")

    op_config = state.rules.operation_types.get(intent.op_type.value)
    if op_config is None:
        base_days = 3
        duration_range = (2, 5)
    else:
        base_days = op_config.base_duration_days
        duration_range = op_config.duration_range

    fort_mod = max(0, int((state.contested_planet.enemy.fortification - 1.0) * 2.0))
    control_mod = max(0, int((1.0 - state.contested_planet.control) * 2.0))
    estimated_days = base_days + fort_mod + control_mod
    estimated_days = max(duration_range[0], min(estimated_days, duration_range[1]))
    if intent.op_type == OperationTypeId.RAID:
        estimated_days = max(3, estimated_days)

    phase_durations = _calculate_phase_durations(intent.op_type, estimated_days)

    enemy = state.contested_planet.enemy
    objective = state.rules.objectives.get(_objective_id(intent.target))
    battlefield = objective.battlefield if objective is not None else None

    fixed_enemy_seeded = False
    foundry_cfg = getattr(state.scenario, "foundry_mvp", None)
    if intent.target == OperationTarget.FOUNDRY and foundry_cfg is not None:
        fixed_enemy_seeded = True
        enemy.infantry = foundry_cfg.enemy_force.infantry
        enemy.walkers = foundry_cfg.enemy_force.walkers
        enemy.support = foundry_cfg.enemy_force.support
        enemy.cohesion = foundry_cfg.enemy_force.cohesion
        enemy.fortification = foundry_cfg.enemy_force.fortification

    attacker = state.task_force

    enemy_power = _power_from_counts(
        enemy.infantry,
        enemy.walkers,
        enemy.support,
        state,
    )
    your_power = _power_from_counts(
        attacker.composition.infantry,
        attacker.composition.walkers,
        attacker.composition.support,
        state,
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
        accumulated_progress=0.0,
        accumulated_losses=0,
        accumulated_enemy_losses=0,
        battle_attacker=BattleSideState(
            infantry=attacker.composition.infantry,
            walkers=attacker.composition.walkers,
            support=attacker.composition.support,
            readiness=attacker.readiness,
            cohesion=attacker.cohesion,
        ),
        battle_defender=BattleSideState(
            infantry=enemy.infantry,
            walkers=enemy.walkers,
            support=enemy.support,
            readiness=enemy.cohesion,
            cohesion=enemy.cohesion,
        ),
        battle_phase_acc=BattlePhaseAccumulator(),
        battle_log=[],
        battlefield=battlefield,
        fixed_enemy_seeded=fixed_enemy_seeded,
        enemy_fortification_start=enemy.fortification,
        enemy_fortification_current=enemy.fortification,
        op_id=str(uuid.uuid4()),
    )


def submit_phase_decisions(
    state: GameState, decisions: Phase1Decisions | Phase2Decisions | Phase3Decisions
) -> None:
    if state.operation is None:
        raise RuntimeError("No active operation")
    if not state.operation.awaiting_player_decision:
        raise RuntimeError("Not awaiting player decision")

    operation = state.operation
    if operation.current_phase == OperationPhase.CONTACT_SHAPING:
        if not isinstance(decisions, Phase1Decisions):
            raise TypeError("Expected Phase1Decisions for Contact/Shaping phase")
        operation.decisions.phase1 = decisions
    elif operation.current_phase == OperationPhase.ENGAGEMENT:
        if not isinstance(decisions, Phase2Decisions):
            raise TypeError("Expected Phase2Decisions for Engagement phase")
        operation.decisions.phase2 = decisions
    elif operation.current_phase == OperationPhase.EXPLOIT_CONSOLIDATE:
        if not isinstance(decisions, Phase3Decisions):
            raise TypeError("Expected Phase3Decisions for Exploit/Consolidate phase")
        operation.decisions.phase3 = decisions
    else:
        raise RuntimeError(f"Cannot submit decisions for phase {operation.current_phase}")

    operation.awaiting_player_decision = False
    operation.phase_start_day = state.day


def acknowledge_phase_result(state: GameState) -> OperationPhaseRecord | None:
    if state.operation is None:
        return None

    operation = state.operation
    record = operation.pending_phase_record
    if record is None:
        return None

    operation.pending_phase_record = None
    operation.advance_phase()

    if operation.current_phase == OperationPhase.COMPLETE:
        _finalize_operation(state)

    return record


def progress_if_applicable(state: GameState, rng, factor_log: FactorLog) -> None:
    if state.operation is None or state.operation.awaiting_player_decision:
        return

    operation = state.operation
    decisions = _current_phase_decisions(operation)
    if decisions is None:
        operation.awaiting_player_decision = True
        return

    phase = operation.current_phase
    operation.day_in_operation += 1
    operation.day_in_phase += 1

    objective = state.rules.objectives.get(_objective_id(operation.target))
    objective_difficulty = objective.base_difficulty if objective is not None else 1.0

    def log(name: str, value: float, delta: str, why: str) -> None:
        factor_log.add(name, value, delta, why, phase)

    battle_result = BattleSimulator.tick_day(
        state=state,
        operation=operation,
        phase=phase,
        decisions=decisions,
        objective_difficulty=objective_difficulty,
        global_day=state.day,
        day_index=operation.day_in_operation,
        rng=rng,
        log=log,
    )

    operation.battle_log.append(battle_result.tick)
    operation.battle_phase_acc.add_day(
        battle_result.tick,
        readiness_delta=battle_result.readiness_delta,
        cohesion_delta=battle_result.cohesion_delta,
        enemy_cohesion_delta=battle_result.enemy_cohesion_delta,
    )

    operation.accumulated_progress += battle_result.tick.progress_delta
    operation.accumulated_losses += sum(battle_result.tick.your_losses.values())
    operation.accumulated_enemy_losses += sum(battle_result.tick.enemy_losses.values())

    _sync_runtime_state(state)

    if operation.is_phase_complete() or battle_result.attacker_collapsed or battle_result.defender_collapsed:
        _close_phase(state, factor_log, phase, decisions)

        if (
            state.operation is not None
            and state.operation.decisions.is_complete()
            and state.operation.auto_advance
        ):
            acknowledge_phase_result(state)
            if state.operation is not None:
                state.operation.awaiting_player_decision = False


def _sync_runtime_state(state: GameState) -> None:
    operation = state.operation
    if operation is None or operation.battle_attacker is None or operation.battle_defender is None:
        return

    attacker = operation.battle_attacker
    defender = operation.battle_defender

    state.task_force.composition.infantry = attacker.infantry
    state.task_force.composition.walkers = attacker.walkers
    state.task_force.composition.support = attacker.support
    state.task_force.readiness = attacker.readiness
    state.task_force.cohesion = attacker.cohesion

    state.contested_planet.enemy.infantry = defender.infantry
    state.contested_planet.enemy.walkers = defender.walkers
    state.contested_planet.enemy.support = defender.support
    state.contested_planet.enemy.cohesion = defender.cohesion
    state.contested_planet.enemy.fortification = operation.enemy_fortification_current


def _close_phase(
    state: GameState,
    factor_log: FactorLog,
    phase: OperationPhase,
    decisions: Phase1Decisions | Phase2Decisions | Phase3Decisions,
) -> None:
    operation = state.operation
    if operation is None:
        return

    phase_days = list(operation.battle_phase_acc.days)
    summary = PhaseSummary(
        progress_delta=operation.battle_phase_acc.progress_delta,
        losses=operation.battle_phase_acc.losses,
        enemy_losses=operation.battle_phase_acc.enemy_losses,
        supplies_spent=Supplies(
            ammo=operation.battle_phase_acc.supplies_spent["ammo"],
            fuel=operation.battle_phase_acc.supplies_spent["fuel"],
            med_spares=operation.battle_phase_acc.supplies_spent["med_spares"],
        ),
        readiness_delta=operation.battle_phase_acc.readiness_delta,
        cohesion_delta=operation.battle_phase_acc.cohesion_delta,
        enemy_cohesion_delta=operation.battle_phase_acc.enemy_cohesion_delta,
    )

    phase_events = [event for event in factor_log.events if event.phase == phase.value]
    record = OperationPhaseRecord(
        phase=phase,
        start_day=operation.phase_start_day,
        end_day=state.day,
        decisions=decisions,
        summary=summary,
        days=phase_days,
        events=phase_events,
    )

    operation.phase_history.append(record)
    operation.pending_phase_record = record
    operation.awaiting_player_decision = True
    operation.battle_phase_acc.reset()


def _calculate_phase_durations(
    op_type: OperationTypeId, total_days: int
) -> dict[OperationPhase, int]:
    if op_type == OperationTypeId.RAID:
        phase_one = 1
        phase_two = 1
        phase_three = max(1, total_days - phase_one - phase_two)
        return {
            OperationPhase.CONTACT_SHAPING: phase_one,
            OperationPhase.ENGAGEMENT: phase_two,
            OperationPhase.EXPLOIT_CONSOLIDATE: phase_three,
        }
    if op_type == OperationTypeId.SIEGE:
        phase_one = max(1, total_days // 3)
        phase_two = max(1, total_days // 2)
        phase_three = max(1, total_days - phase_one - phase_two)
        return {
            OperationPhase.CONTACT_SHAPING: phase_one,
            OperationPhase.ENGAGEMENT: phase_two,
            OperationPhase.EXPLOIT_CONSOLIDATE: phase_three,
        }

    phase_one = max(1, total_days // 3)
    phase_two = max(1, total_days // 3)
    phase_three = max(1, total_days - phase_one - phase_two)
    return {
        OperationPhase.CONTACT_SHAPING: phase_one,
        OperationPhase.ENGAGEMENT: phase_two,
        OperationPhase.EXPLOIT_CONSOLIDATE: phase_three,
    }


def _current_phase_decisions(
    operation: ActiveOperation,
) -> Phase1Decisions | Phase2Decisions | Phase3Decisions | None:
    if operation.current_phase == OperationPhase.CONTACT_SHAPING:
        return operation.decisions.phase1
    if operation.current_phase == OperationPhase.ENGAGEMENT:
        return operation.decisions.phase2
    if operation.current_phase == OperationPhase.EXPLOIT_CONSOLIDATE:
        return operation.decisions.phase3
    return None


def _finalize_operation(state: GameState) -> None:
    operation = state.operation
    if operation is None:
        return

    all_events: list[FactorEvent] = []
    for record in operation.phase_history:
        all_events.extend(record.events)

    phase_three = operation.decisions.phase3
    end_state = phase_three.end_state if phase_three else "withdraw"
    end_rules = state.rules.end_states.get(
        end_state,
        {
            "required_progress": 0.75,
            "fortification_reduction": 0.0,
            "reinforcement_reduction": 0.0,
        },
    )

    required_progress = float(end_rules.get("required_progress", 0.75))
    success = operation.accumulated_progress >= required_progress

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
        fort_reduction = float(end_rules.get("fortification_reduction", 0.0))
        reinforcement_reduction = float(end_rules.get("reinforcement_reduction", 0.0))
        if end_state == "capture":
            _set_objective(state, operation.target, ObjectiveStatus.SECURED)
            state.contested_planet.control = min(1.0, state.contested_planet.control + 0.15)
        elif end_state == "raid":
            state.contested_planet.control = min(1.0, state.contested_planet.control + 0.05)
        elif end_state == "destroy":
            state.contested_planet.control = min(1.0, state.contested_planet.control + 0.10)

        state.contested_planet.enemy.fortification = max(
            0.6,
            state.contested_planet.enemy.fortification - fort_reduction,
        )
        state.contested_planet.enemy.reinforcement_rate = max(
            0.0,
            state.contested_planet.enemy.reinforcement_rate - reinforcement_reduction,
        )
    elif end_state != "withdraw":
        state.contested_planet.control = max(0.0, state.contested_planet.control - 0.10)
        state.contested_planet.enemy.fortification = min(
            2.5,
            state.contested_planet.enemy.fortification + 0.10,
        )

    _update_intel_confidence(state, operation, success)

    state.last_aar = AfterActionReport(
        outcome=outcome,
        target=operation.target,
        operation_type=operation.op_type.value,
        days=operation.day_in_operation,
        losses=operation.accumulated_losses,
        enemy_losses=operation.accumulated_enemy_losses,
        remaining_supplies=state.front_supplies,
        top_factors=_top_factors(all_events),
        phases=list(operation.phase_history),
        events=all_events,
    )
    state.operation = None


def _top_factors(events: list[FactorEvent]) -> list[TopFactor]:
    scored: list[tuple[float, FactorEvent]] = []
    for event in events:
        scored.append((abs(event.value), event))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        TopFactor(name=event.name, value=event.value, delta=event.delta, why=event.why)
        for _, event in scored[:5]
    ]


def _update_intel_confidence(state: GameState, operation: ActiveOperation, success: bool) -> None:
    enemy = state.contested_planet.enemy
    gain = 0.02

    if operation.decisions.phase1:
        axis = operation.decisions.phase1.approach_axis
        if axis == "stealth":
            gain += 0.03
        elif axis == "dispersed":
            gain += 0.02

    support_role = state.rules.unit_roles.get("support")
    if support_role and support_role.recon:
        gain += min(0.05, state.task_force.composition.support * 0.005)

    if success:
        gain += 0.02

    enemy.intel_confidence = min(0.95, max(0.05, enemy.intel_confidence + gain))


def _objective_id(target: OperationTarget) -> str:
    if target == OperationTarget.FOUNDRY:
        return "foundry"
    if target == OperationTarget.COMMS:
        return "comms"
    return "power"


def _set_objective(state: GameState, target: OperationTarget, status: ObjectiveStatus) -> None:
    if target == OperationTarget.FOUNDRY:
        state.contested_planet.objectives.foundry = status
    elif target == OperationTarget.COMMS:
        state.contested_planet.objectives.comms = status
    elif target == OperationTarget.POWER:
        state.contested_planet.objectives.power = status


def _get_objective_status(state: GameState, target: OperationTarget) -> ObjectiveStatus:
    if target == OperationTarget.FOUNDRY:
        return state.contested_planet.objectives.foundry
    if target == OperationTarget.COMMS:
        return state.contested_planet.objectives.comms
    return state.contested_planet.objectives.power


def _power_from_counts(infantry: int, walkers: int, support: int, state: GameState) -> float:
    infantry_power = state.rules.unit_roles.get("infantry").base_power if state.rules.unit_roles.get("infantry") else 1.0
    walker_power = state.rules.unit_roles.get("walkers").base_power if state.rules.unit_roles.get("walkers") else 12.0
    support_power = state.rules.unit_roles.get("support").base_power if state.rules.unit_roles.get("support") else 4.0
    return (infantry * infantry_power) + (walkers * walker_power) + (support * support_power)
