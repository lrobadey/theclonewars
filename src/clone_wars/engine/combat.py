from __future__ import annotations


def calculate_power(
    infantry: int,
    walkers: int,
    support: int,
    cohesion: float,
    supply_mod: float = 1.0,
    fortification: float = 1.0,
) -> float:
    if infantry <= 0 and walkers <= 0 and support <= 0:
        return 0.0
    base = infantry * 1.0 + walkers * 12.0 + support * 4.0
    cohesion_mod = max(0.0, min(1.0, cohesion))
    return base * cohesion_mod * supply_mod / max(0.5, fortification)


__all__ = ["calculate_power"]
