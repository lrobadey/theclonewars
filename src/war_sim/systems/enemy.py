from __future__ import annotations

from war_sim.sim.state import GameState


def passive_tick(state: GameState, rng) -> None:
    base_reinforcement_rate = 0.10
    planet = state.contested_planet
    reinforcement_scale = (
        planet.enemy.reinforcement_rate / base_reinforcement_rate
        if base_reinforcement_rate > 0
        else 0.0
    )
    reinforcement_scale = min(2.0, max(0.0, reinforcement_scale))
    enemy = planet.enemy
    if state.operation is None:
        enemy.fortification = min(2.5, enemy.fortification + (0.03 * reinforcement_scale))
        enemy.infantry = min(5000, enemy.infantry + int(round(5 * reinforcement_scale)))
        if rng.random() < (0.05 * reinforcement_scale):
            enemy.walkers = min(200, enemy.walkers + 1)
        if rng.random() < (0.07 * reinforcement_scale):
            enemy.support = min(500, enemy.support + 1)

        enemy.cohesion = min(1.0, enemy.cohesion + (0.15 * reinforcement_scale))
    else:
        enemy.fortification = min(2.0, enemy.fortification + (0.01 * reinforcement_scale))
        enemy.cohesion = min(1.0, enemy.cohesion + (0.05 * reinforcement_scale))
