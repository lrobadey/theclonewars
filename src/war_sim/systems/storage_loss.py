from __future__ import annotations

from war_sim.domain.types import Supplies
from war_sim.sim.state import GameState


def apply_storage_loss(state: GameState, rng) -> None:
    storage_risk_per_day = state.rules.globals.storage_risk_per_day
    storage_loss_pct_range = state.rules.globals.storage_loss_pct_range
    for location_id in state.logistics.depot_stocks.keys():
        risk = storage_risk_per_day.get(location_id, 0.0)
        if risk <= 0:
            continue
        stock = state.logistics.depot_stocks[location_id]
        if stock.ammo == 0 and stock.fuel == 0 and stock.med_spares == 0:
            continue
        if rng.random() >= risk:
            continue
        min_loss, max_loss = storage_loss_pct_range.get(location_id, (0.0, 0.0))
        loss_pct = min_loss + (rng.random() * (max_loss - min_loss))
        state.logistics.depot_stocks[location_id] = Supplies(
            ammo=max(0, int(stock.ammo * (1 - loss_pct))),
            fuel=max(0, int(stock.fuel * (1 - loss_pct))),
            med_spares=max(0, int(stock.med_spares * (1 - loss_pct))),
        )
