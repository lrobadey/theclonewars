from __future__ import annotations

from war_sim.systems.combat import *  # noqa: F401,F403


def execute_raid(state, rng):
    """Legacy wrapper for tests: run a full raid combat session and return CombatResult."""
    session = start_raid_session(state, rng)
    while session.outcome is None:
        session.step()
    return session.to_result()


__all__ = [
    "CombatResult",
    "CombatTick",
    "RaidCombatSession",
    "RaidFactor",
    "RaidBeat",
    "calculate_power",
    "execute_raid",
    "get_beat",
    "start_raid_session",
]
