from __future__ import annotations

import uuid
from dataclasses import dataclass

from war_sim.domain.events import FactorEvent, FactorScope
from war_sim.domain.ops_models import OperationTarget
from war_sim.domain.reports import RaidReport, TopFactor
from war_sim.domain.types import LocationId, ObjectiveStatus, Supplies
from war_sim.sim.state import GameState
from war_sim.systems.combat import CombatTick, RaidCombatSession, start_raid_session


def start_raid(state: GameState, target: OperationTarget, rng) -> None:
    if state.operation is not None or state.raid_session is not None:
        raise RuntimeError("Only one active operation allowed")
    if _get_objective_status(state, target) == ObjectiveStatus.SECURED:
        raise RuntimeError(f"Cannot raid {target.value}; objective already secured")
    state.raid_target = target
    state.raid_id = str(uuid.uuid4())
    state.raid_session = start_raid_session(state, rng)


def advance_raid_tick(state: GameState) -> CombatTick | None:
    if state.raid_session is None:
        raise RuntimeError("No active raid")
    tick = state.raid_session.step()
    if state.raid_session.outcome is not None:
        _finalize_raid(state)
    return tick


def resolve_active_raid(state: GameState) -> RaidReport:
    if state.raid_session is None:
        raise RuntimeError("No active raid")
    while state.raid_session is not None:
        advance_raid_tick(state)
    report = state.last_aar
    if not isinstance(report, RaidReport):
        raise RuntimeError("Raid did not produce report")
    return report


def raid(state: GameState, target: OperationTarget, rng) -> RaidReport:
    if state.raid_session is not None:
        raise RuntimeError("Only one active operation allowed")
    start_raid(state, target, rng)
    return resolve_active_raid(state)


def _finalize_raid(state: GameState) -> None:
    if state.raid_session is None or state.raid_target is None:
        return

    initial_units = (
        state.task_force.composition.infantry
        + state.task_force.composition.walkers
        + state.task_force.composition.support
    )

    result = state.raid_session.to_result()

    state.task_force.composition.infantry = result.your_remaining["infantry"]
    state.task_force.composition.walkers = result.your_remaining["walkers"]
    state.task_force.composition.support = result.your_remaining["support"]

    _set_front_supplies(
        state,
        Supplies(
            ammo=state.front_supplies.ammo - result.supplies_consumed.ammo,
            fuel=state.front_supplies.fuel - result.supplies_consumed.fuel,
            med_spares=state.front_supplies.med_spares - result.supplies_consumed.med_spares,
        ).clamp_non_negative(),
    )

    casualty_ratio = result.your_casualties_total / max(1, initial_units)
    readiness_drop = min(0.35, (0.02 * result.ticks) + (0.25 * casualty_ratio))
    state.task_force.readiness = max(0.0, min(1.0, state.task_force.readiness - readiness_drop))
    state.task_force.cohesion = state.task_force.readiness

    enemy = state.contested_planet.enemy
    enemy.infantry = result.enemy_remaining["infantry"]
    enemy.walkers = result.enemy_remaining["walkers"]
    enemy.support = result.enemy_remaining["support"]
    enemy.cohesion = max(0.0, min(1.0, result.enemy_final_cohesion))

    victory = result.outcome == "VICTORY"
    _apply_raid_outcome(state, state.raid_target, victory=victory)

    key_moments: list[str] = []
    last_event: str | None = None
    for tick in result.tick_log:
        if tick.event != last_event:
            key_moments.append(f"T{tick.tick}: {tick.event}")
            last_event = tick.event
        if len(key_moments) >= 5:
            break

    scope = FactorScope(kind="raid", id=state.raid_id or "raid")
    factor_events = [
        FactorEvent(
            name=factor.name,
            value=factor.value,
            delta="combat",
            why=factor.why,
            phase="raid",
            scope=scope,
        )
        for factor in result.top_factors
    ]
    top_factors = [
        TopFactor(name=f.name, value=f.value, delta="combat", why=f.why) for f in result.top_factors
    ]

    report = RaidReport(
        outcome=result.outcome,
        reason=result.reason,
        target=state.raid_target,
        ticks=result.ticks,
        your_casualties=result.your_casualties_total,
        enemy_casualties=result.enemy_casualties_total,
        your_remaining=dict(result.your_remaining),
        enemy_remaining=dict(result.enemy_remaining),
        supplies_used=result.supplies_consumed,
        key_moments=key_moments,
        tick_log=result.tick_log,
        top_factors=top_factors,
        events=factor_events,
    )
    state.last_aar = report
    state.raid_session = None
    state.raid_target = None
    state.raid_id = None


def _apply_raid_outcome(state: GameState, target: OperationTarget, *, victory: bool) -> None:
    planet = state.contested_planet
    prior = _get_objective_status(state, target)
    if victory:
        planet.control = min(1.0, planet.control + 0.05)
        planet.enemy.fortification = max(0.6, planet.enemy.fortification - 0.03)

        if prior == ObjectiveStatus.ENEMY:
            _set_objective(state, target, ObjectiveStatus.CONTESTED)
        elif prior == ObjectiveStatus.CONTESTED:
            _set_objective(state, target, ObjectiveStatus.SECURED)
            planet.enemy.reinforcement_rate = max(0.0, planet.enemy.reinforcement_rate - 0.02)
            planet.enemy.fortification = max(0.6, planet.enemy.fortification - 0.10)
    else:
        planet.control = max(0.0, planet.control - 0.05)
        planet.enemy.fortification = min(2.5, planet.enemy.fortification + 0.03)


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
