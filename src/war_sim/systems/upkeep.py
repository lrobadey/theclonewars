from __future__ import annotations

from war_sim.domain.types import LocationId, Supplies
from war_sim.sim.state import GameState


def apply_daily_upkeep(state: GameState) -> None:
    upkeep_fuel = 2
    upkeep_med = 1
    tf_supplies = state.front_supplies
    new_fuel = max(0, tf_supplies.fuel - upkeep_fuel)
    new_med = max(0, tf_supplies.med_spares - upkeep_med)
    state.logistics.depot_stocks[LocationId.CONTESTED_FRONT] = Supplies(
        ammo=tf_supplies.ammo,
        fuel=new_fuel,
        med_spares=new_med,
    )
    state.task_force.supplies = Supplies(
        ammo=tf_supplies.ammo,
        fuel=new_fuel,
        med_spares=new_med,
    )
    if new_fuel == 0 or new_med == 0:
        state.task_force.readiness = max(0.0, state.task_force.readiness - 0.02)
