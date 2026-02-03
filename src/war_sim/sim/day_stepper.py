from __future__ import annotations

from war_sim.domain.types import LocationId, Supplies, UnitStock
from war_sim.sim.state import GameState
from war_sim.systems import enemy, logistics as logistics_module, storage_loss, upkeep
from war_sim.systems.barracks import BarracksOutput, BarracksJobType
from war_sim.systems.operations import FactorLog, progress_if_applicable
from war_sim.systems.production import ProductionJobType, ProductionOutput


class DayAdvanceError(RuntimeError):
    pass


def advance_day(state: GameState, rng_provider, factor_log: FactorLog) -> None:
    if state.raid_session is not None:
        raise DayAdvanceError("Raid in progress")
    if state.operation is not None:
        op = state.operation
        if op.pending_phase_record is not None:
            raise DayAdvanceError("Acknowledge phase report")
        if op.awaiting_player_decision:
            raise DayAdvanceError("Awaiting phase orders")

    state.day += 1

    _tick_production_and_distribute_to_core(state, rng_provider("production", "tick"))
    _tick_barracks_and_distribute_to_core(state, rng_provider("barracks", "tick"))

    logistics_module.LogisticsService().tick(
        state.logistics, state.contested_planet, rng_provider("logistics", "tick"), state.day
    )
    _sync_task_force_supplies(state)

    upkeep.apply_daily_upkeep(state)
    enemy.passive_tick(state, rng_provider("enemy", "passive"))
    storage_loss.apply_storage_loss(state, rng_provider("storage", "loss"))

    progress_if_applicable(state, rng_provider("ops", "progress"), factor_log)


def _tick_production_and_distribute_to_core(state: GameState, rng) -> None:
    completed = state.production.tick()
    for output in completed:
        _apply_production_output(state, output, rng)


def _tick_barracks_and_distribute_to_core(state: GameState, rng) -> None:
    completed = state.barracks.tick()
    for output in completed:
        _apply_barracks_output(state, output, rng)


def _apply_production_output(state: GameState, output: ProductionOutput, rng) -> None:
    job_type = output.job_type
    quantity = output.quantity
    core_id = LocationId.NEW_SYSTEM_CORE

    core_stock = state.logistics.depot_stocks[core_id]
    core_units = state.logistics.depot_units[core_id]
    supplies, units = _build_production_payload(job_type, quantity)
    if job_type == ProductionJobType.AMMO:
        state.logistics.depot_stocks[core_id] = Supplies(
            ammo=core_stock.ammo + quantity,
            fuel=core_stock.fuel,
            med_spares=core_stock.med_spares,
        )
    elif job_type == ProductionJobType.FUEL:
        state.logistics.depot_stocks[core_id] = Supplies(
            ammo=core_stock.ammo,
            fuel=core_stock.fuel + quantity,
            med_spares=core_stock.med_spares,
        )
    elif job_type == ProductionJobType.MED_SPARES:
        state.logistics.depot_stocks[core_id] = Supplies(
            ammo=core_stock.ammo,
            fuel=core_stock.fuel,
            med_spares=core_stock.med_spares + quantity,
        )
    elif job_type == ProductionJobType.WALKERS:
        state.logistics.depot_units[core_id] = UnitStock(
            infantry=core_units.infantry,
            walkers=core_units.walkers + quantity,
            support=core_units.support,
        )
    else:
        raise ValueError(f"Unsupported production job type: {job_type}")

    if output.stop_at != core_id:
        try:
            logistics_module.LogisticsService().create_shipment(
                state.logistics,
                core_id,
                output.stop_at,
                supplies,
                units,
                rng,
                current_day=state.day,
            )
        except ValueError:
            pass


def _apply_barracks_output(state: GameState, output: BarracksOutput, rng) -> None:
    job_type = output.job_type
    quantity = output.quantity
    core_id = LocationId.NEW_SYSTEM_CORE

    core_units = state.logistics.depot_units[core_id]
    supplies, units = _build_barracks_payload(job_type, quantity)

    if job_type == BarracksJobType.INFANTRY:
        state.logistics.depot_units[core_id] = UnitStock(
            infantry=core_units.infantry + quantity,
            walkers=core_units.walkers,
            support=core_units.support,
        )
    elif job_type == BarracksJobType.SUPPORT:
        state.logistics.depot_units[core_id] = UnitStock(
            infantry=core_units.infantry,
            walkers=core_units.walkers,
            support=core_units.support + quantity,
        )
    else:
        raise ValueError(f"Unsupported barracks job type: {job_type}")

    if output.stop_at != core_id:
        try:
            logistics_module.LogisticsService().create_shipment(
                state.logistics,
                core_id,
                output.stop_at,
                supplies,
                units,
                rng,
                current_day=state.day,
            )
        except ValueError:
            pass


def _build_production_payload(
    job_type: ProductionJobType, quantity: int
) -> tuple[Supplies, UnitStock]:
    if job_type == ProductionJobType.AMMO:
        return Supplies(ammo=quantity, fuel=0, med_spares=0), UnitStock(0, 0, 0)
    if job_type == ProductionJobType.FUEL:
        return Supplies(ammo=0, fuel=quantity, med_spares=0), UnitStock(0, 0, 0)
    if job_type == ProductionJobType.MED_SPARES:
        return Supplies(ammo=0, fuel=0, med_spares=quantity), UnitStock(0, 0, 0)
    if job_type == ProductionJobType.WALKERS:
        return Supplies(0, 0, 0), UnitStock(infantry=0, walkers=quantity, support=0)
    raise ValueError(f"Unsupported production job type: {job_type}")


def _build_barracks_payload(
    job_type: BarracksJobType, quantity: int
) -> tuple[Supplies, UnitStock]:
    if job_type == BarracksJobType.INFANTRY:
        return Supplies(0, 0, 0), UnitStock(infantry=quantity, walkers=0, support=0)
    if job_type == BarracksJobType.SUPPORT:
        return Supplies(0, 0, 0), UnitStock(infantry=0, walkers=0, support=quantity)
    raise ValueError(f"Unsupported barracks job type: {job_type}")


def _sync_task_force_supplies(state: GameState) -> None:
    state.task_force.supplies = state.logistics.depot_stocks[LocationId.CONTESTED_FRONT]
