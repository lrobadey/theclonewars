from __future__ import annotations

from war_sim.systems.battle_sim import compute_force_limit


def test_foundry_force_limit_formula() -> None:
    force_limit = compute_force_limit(infrastructure=18, combat_width_multiplier=0.35)
    assert force_limit == 5
