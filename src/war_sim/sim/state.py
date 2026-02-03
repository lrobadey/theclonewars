"""Simulation state container."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from war_sim.domain.ops_models import ActiveOperation, OperationTarget
from war_sim.domain.reports import AfterActionReport, RaidReport
from war_sim.domain.types import (
    FactionId,
    LocationId,
    PlanetState,
    TaskForceState,
)
from war_sim.rules.ruleset import Ruleset
from war_sim.systems.barracks import BarracksState
from war_sim.systems.logistics import LogisticsService, LogisticsState
from war_sim.systems.production import ProductionState
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from war_sim.rules.scenario import ScenarioData
    from war_sim.systems.raid import RaidCombatSession


@dataclass()
class GameState:
    day: int
    rng_seed: int
    action_seq: int

    planets: dict[LocationId, PlanetState]
    production: ProductionState
    barracks: BarracksState
    logistics: LogisticsState
    task_force: TaskForceState
    rules: Ruleset
    scenario: "ScenarioData"

    action_points: int
    faction_turn: FactionId

    raid_session: "RaidCombatSession" | None
    raid_target: OperationTarget | None
    raid_id: str | None
    operation: ActiveOperation | None
    last_aar: RaidReport | AfterActionReport | None

    logistics_service: LogisticsService = field(default_factory=LogisticsService, init=False)

    @property
    def contested_planet(self) -> PlanetState:
        return self.planets[LocationId.CONTESTED_SPACEPORT]

    @property
    def front_supplies(self):
        return self.logistics.depot_stocks[LocationId.CONTESTED_FRONT]

    @property
    def rng(self) -> Random:
        """Legacy RNG accessor for compatibility."""
        return Random(self.rng_seed)

    def set_front_supplies(self, supplies) -> None:
        self.logistics.depot_stocks[LocationId.CONTESTED_FRONT] = supplies
        self.task_force.supplies = supplies

    def advance_day(self) -> None:
        from war_sim.domain.events import FactorScope
        from war_sim.sim.day_stepper import advance_day
        from war_sim.sim.rng import derive_seed
        from war_sim.systems.operations import FactorLog

        next_seq = self.action_seq + 1

        def rng_provider(stream: str, purpose: str) -> Random:
            return Random(
                derive_seed(
                    self.rng_seed, day=self.day, action_seq=next_seq, stream=stream, purpose=purpose
                )
            )

        scope_id = self.operation.op_id if self.operation else "none"
        factor_log = FactorLog(scope=FactorScope(kind="operation", id=scope_id))
        advance_day(self, rng_provider, factor_log)
        self.action_seq = next_seq

    def start_operation(self, plan) -> None:
        from war_sim.sim.rng import derive_seed
        from war_sim.systems.operations import start_operation

        rng = Random(
            derive_seed(
                self.rng_seed,
                day=self.day,
                action_seq=self.action_seq + 1,
                stream="ops",
                purpose="start",
            )
        )
        start_operation(self, plan, rng)
        self.action_seq += 1

    def start_operation_phased(self, intent) -> None:
        from war_sim.sim.rng import derive_seed
        from war_sim.systems.operations import start_operation_phased

        rng = Random(
            derive_seed(
                self.rng_seed,
                day=self.day,
                action_seq=self.action_seq + 1,
                stream="ops",
                purpose="start",
            )
        )
        start_operation_phased(self, intent, rng)
        self.action_seq += 1

    def submit_phase_decisions(self, decisions) -> None:
        from war_sim.systems.operations import submit_phase_decisions

        submit_phase_decisions(self, decisions)

    def acknowledge_phase_result(self):
        from war_sim.systems.operations import acknowledge_phase_result

        return acknowledge_phase_result(self)

    def start_raid(self, target) -> None:
        from war_sim.sim.rng import derive_seed
        from war_sim.systems import raid

        rng = Random(
            derive_seed(
                self.rng_seed,
                day=self.day,
                action_seq=self.action_seq + 1,
                stream="raid",
                purpose="start",
            )
        )
        raid.start_raid(self, target, rng)
        self.action_seq += 1

    def advance_raid_tick(self):
        from war_sim.systems import raid

        return raid.advance_raid_tick(self)

    def resolve_active_raid(self):
        from war_sim.systems import raid

        return raid.resolve_active_raid(self)

    def raid(self, target):
        from war_sim.sim.rng import derive_seed
        from war_sim.systems import raid

        rng = Random(
            derive_seed(
                self.rng_seed,
                day=self.day,
                action_seq=self.action_seq + 1,
                stream="raid",
                purpose="start",
            )
        )
        report = raid.raid(self, target, rng)
        self.action_seq += 1
        return report
