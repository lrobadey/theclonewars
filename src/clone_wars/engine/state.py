from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from random import Random

from clone_wars.engine.combat import (
    CombatTick,
    RaidCombatSession,
    RaidFactor,
    calculate_power,
    start_raid_session,
)
from clone_wars.engine.logging import Event, TopFactor
from clone_wars.engine.logistics import (
    LogisticsState,
)
from clone_wars.engine.ops import (
    ActiveOperation,
    OperationDecisions,
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
from clone_wars.engine.barracks import BarracksJobType, BarracksOutput, BarracksState
from clone_wars.engine.production import ProductionJobType, ProductionOutput, ProductionState
from clone_wars.engine.rules import Ruleset, RulesError
from clone_wars.engine.services.logistics import LogisticsService
from clone_wars.engine.types import (
    EnemyForce,
    FactionId,
    LocationId,
    Objectives,
    ObjectiveStatus,
    PlanetState,
    Supplies,
    UnitStock,
)

# ProductionState moved to production.py module


@dataclass()
class UnitComposition:
    infantry: int
    walkers: int
    support: int


@dataclass()
class TaskForceState:
    composition: UnitComposition
    readiness: float
    cohesion: float
    supplies: Supplies
    location: LocationId = LocationId.CONTESTED_SPACEPORT


@dataclass(frozen=True)
class RaidReport:
    outcome: str  # "VICTORY" / "DEFEAT" / "STALEMATE"
    reason: str
    target: OperationTarget
    ticks: int
    your_casualties: int
    enemy_casualties: int
    your_remaining: dict[str, int]
    enemy_remaining: dict[str, int]
    supplies_used: Supplies
    key_moments: list[str]
    tick_log: list[CombatTick]
    top_factors: list[RaidFactor] = field(default_factory=list)


@dataclass(frozen=True)
class AfterActionReport:
    outcome: str
    target: OperationTarget
    operation_type: str
    days: int
    losses: int
    remaining_supplies: Supplies
    top_factors: list[TopFactor]
    phases: list[OperationPhaseRecord]
    events: list[Event]


@dataclass()
class GameState:
    day: int
    rng_seed: int
    rng: Random

    planets: dict[LocationId, PlanetState]
    production: ProductionState
    barracks: BarracksState
    logistics: LogisticsState
    task_force: TaskForceState
    rules: Ruleset
    
    action_points: int
    faction_turn: FactionId
    
    logistics_service: LogisticsService = field(default_factory=LogisticsService, init=False)

    raid_session: RaidCombatSession | None
    raid_target: OperationTarget | None
    operation: ActiveOperation | None
    last_aar: RaidReport | AfterActionReport | None

    @staticmethod
    def new(seed: int = 1, data_dir: Path | None = None) -> "GameState":
        rng = Random(seed)
        if data_dir is None:
            data_dir = Path(__file__).resolve().parents[1] / "data"
        try:
            rules = Ruleset.load(data_dir)
        except RulesError as exc:
            raise RuntimeError(f"Failed to load rules: {exc}") from exc

        prod_cfg = rules.production
        barracks_cfg = rules.barracks

        contested_planet = PlanetState(
            objectives=Objectives(
                foundry=ObjectiveStatus.ENEMY,
                comms=ObjectiveStatus.ENEMY,
                power=ObjectiveStatus.ENEMY,
            ),
            enemy=EnemyForce(
                infantry=120,
                walkers=2,
                support=1,
                cohesion=1.00,
                fortification=1.20,
                reinforcement_rate=0.0,
                intel_confidence=0.70,
            ),
            control=0.3,  # Initial control level
        )

        logistics = LogisticsState.new()
        front_supplies = logistics.depot_stocks[LocationId.CONTESTED_FRONT]

        return GameState(
            day=1,
            rng_seed=seed,
            rng=rng,
            planets={LocationId.CONTESTED_SPACEPORT: contested_planet},
            production=ProductionState.new(
                factories=3,
                slots_per_factory=prod_cfg.slots_per_factory,
                max_factories=prod_cfg.max_factories,
                queue_policy=prod_cfg.queue_policy,
                costs=prod_cfg.costs,
            ),
            barracks=BarracksState.new(
                barracks=2,
                slots_per_barracks=barracks_cfg.slots_per_barracks,
                max_barracks=barracks_cfg.max_barracks,
                queue_policy=barracks_cfg.queue_policy,
                costs=barracks_cfg.costs,
            ),
            logistics=logistics,
            task_force=TaskForceState(
                composition=UnitComposition(infantry=120, walkers=2, support=1),
                readiness=1.00,
                cohesion=1.00,
                supplies=front_supplies,
                location=LocationId.CONTESTED_SPACEPORT,
            ),
            rules=rules,
            action_points=3,
            faction_turn=FactionId.NEW_SYSTEM,
            raid_session=None,
            raid_target=None,
            operation=None,
            last_aar=None,
        )

    @property
    def contested_planet(self) -> PlanetState:
        """Helper to access the main contested planet (MVP assumption)."""
        return self.planets[LocationId.CONTESTED_SPACEPORT]

    @property
    def front_supplies(self) -> Supplies:
        return self.logistics.depot_stocks[LocationId.CONTESTED_FRONT]

    def set_front_supplies(self, supplies: Supplies) -> None:
        self.logistics.depot_stocks[LocationId.CONTESTED_FRONT] = supplies
        self.task_force.supplies = supplies

    def _sync_task_force_supplies(self) -> None:
        self.task_force.supplies = self.front_supplies

    def advance_day(self) -> None:
        """Advance game state by one day."""
        if self.raid_session is not None:
            return
        self.day += 1
        self._tick_production_and_distribute_to_core()
        self._tick_barracks_and_distribute_to_core()
        self._tick_logistics()
        self._resupply_task_force_daily()
        self._apply_daily_upkeep()
        self._apply_enemy_passive_reactions()
        self._apply_storage_loss_events()
        self._progress_operation_if_applicable()

    def start_raid(self, target: OperationTarget) -> None:
        if self.operation is not None or self.raid_session is not None:
            raise RuntimeError("Only one active operation allowed")
        # Use contested planet helper
        planet = self.contested_planet
        if self._get_objective_status(target) == ObjectiveStatus.SECURED:
            raise RuntimeError(f"Cannot raid {target.value}; objective already secured")
        self.raid_target = target
        self.raid_session = start_raid_session(self, self.rng)

    def advance_raid_tick(self) -> CombatTick | None:
        if self.raid_session is None:
            raise RuntimeError("No active raid")
        tick = self.raid_session.step()
        if self.raid_session.outcome is not None:
            self._finalize_raid()
        return tick

    def resolve_active_raid(self) -> RaidReport:
        if self.raid_session is None:
            raise RuntimeError("No active raid")
        while self.raid_session is not None:
            self.advance_raid_tick()
        report = self.last_aar
        if not isinstance(report, RaidReport):
            raise RuntimeError("Raid did not produce report")
        return report

    def raid(self, target: OperationTarget) -> RaidReport:
        if self.raid_session is not None:
            raise RuntimeError("Only one active operation allowed")
        self.start_raid(target)
        return self.resolve_active_raid()

    def _finalize_raid(self) -> None:
        if self.raid_session is None or self.raid_target is None:
            return

        initial_units = (
            self.task_force.composition.infantry
            + self.task_force.composition.walkers
            + self.task_force.composition.support
        )

        result = self.raid_session.to_result()

        self.task_force.composition.infantry = result.your_remaining["infantry"]
        self.task_force.composition.walkers = result.your_remaining["walkers"]
        self.task_force.composition.support = result.your_remaining["support"]

        self.set_front_supplies(
            Supplies(
                ammo=self.front_supplies.ammo - result.supplies_consumed.ammo,
                fuel=self.front_supplies.fuel - result.supplies_consumed.fuel,
                med_spares=self.front_supplies.med_spares - result.supplies_consumed.med_spares,
            ).clamp_non_negative()
        )

        casualty_ratio = result.your_casualties_total / max(1, initial_units)
        readiness_drop = min(0.35, (0.02 * result.ticks) + (0.25 * casualty_ratio))
        self.task_force.readiness = max(0.0, min(1.0, self.task_force.readiness - readiness_drop))
        self.task_force.cohesion = self.task_force.readiness

        enemy = self.contested_planet.enemy
        enemy.infantry = result.enemy_remaining["infantry"]
        enemy.walkers = result.enemy_remaining["walkers"]
        enemy.support = result.enemy_remaining["support"]
        enemy.cohesion = max(0.0, min(1.0, result.enemy_final_cohesion))

        victory = result.outcome == "VICTORY"
        self._apply_raid_outcome(self.raid_target, victory=victory)

        key_moments: list[str] = []
        last_event: str | None = None
        for tick in result.tick_log:
            if tick.event != last_event:
                key_moments.append(f"T{tick.tick}: {tick.event}")
                last_event = tick.event
            if len(key_moments) >= 5:
                break

        report = RaidReport(
            outcome=result.outcome,
            reason=result.reason,
            target=self.raid_target,
            ticks=result.ticks,
            your_casualties=result.your_casualties_total,
            enemy_casualties=result.enemy_casualties_total,
            your_remaining=dict(result.your_remaining),
            enemy_remaining=dict(result.enemy_remaining),
            supplies_used=result.supplies_consumed,
            key_moments=key_moments,
            tick_log=result.tick_log,
            top_factors=result.top_factors,
        )
        self.last_aar = report
        self.raid_session = None
        self.raid_target = None

    def _apply_raid_outcome(self, target: OperationTarget, *, victory: bool) -> None:
        planet = self.contested_planet
        prior = self._get_objective_status(target)
        if victory:
            planet.control = min(1.0, planet.control + 0.05)
            planet.enemy.fortification = max(0.6, planet.enemy.fortification - 0.03)

            if prior == ObjectiveStatus.ENEMY:
                self._set_objective(target, ObjectiveStatus.CONTESTED)
            elif prior == ObjectiveStatus.CONTESTED:
                self._set_objective(target, ObjectiveStatus.SECURED)
                planet.enemy.reinforcement_rate = max(0.0, planet.enemy.reinforcement_rate - 0.02)
                planet.enemy.fortification = max(0.6, planet.enemy.fortification - 0.10)
        else:
            planet.control = max(0.0, planet.control - 0.05)
            planet.enemy.fortification = min(2.5, planet.enemy.fortification + 0.05)
            if prior == ObjectiveStatus.CONTESTED:
                self._set_objective(target, ObjectiveStatus.ENEMY)

    def _tick_production_and_distribute_to_core(self) -> None:
        """Run production tick and distribute completed items to Core depot."""
        completed = self.production.tick()
        for output in completed:
            self._apply_production_output(output)

    def _tick_barracks_and_distribute_to_core(self) -> None:
        """Run barracks tick and distribute completed items to Core depot."""
        completed = self.barracks.tick()
        for output in completed:
            self._apply_barracks_output(output)

    def _apply_production_output(self, output: ProductionOutput) -> None:
        """Add completed production output to Core depot, then auto-dispatch if needed."""
        job_type = output.job_type
        quantity = output.quantity
        core_id = LocationId.NEW_SYSTEM_CORE
        
        core_stock = self.logistics.depot_stocks[core_id]
        core_units = self.logistics.depot_units[core_id]
        supplies, units = self._build_production_payload(job_type, quantity)
        if job_type == ProductionJobType.AMMO:
            self.logistics.depot_stocks[core_id] = Supplies(
                ammo=core_stock.ammo + quantity,
                fuel=core_stock.fuel,
                med_spares=core_stock.med_spares,
            )
        elif job_type == ProductionJobType.FUEL:
            self.logistics.depot_stocks[core_id] = Supplies(
                ammo=core_stock.ammo,
                fuel=core_stock.fuel + quantity,
                med_spares=core_stock.med_spares,
            )
        elif job_type == ProductionJobType.MED_SPARES:
            self.logistics.depot_stocks[core_id] = Supplies(
                ammo=core_stock.ammo,
                fuel=core_stock.fuel,
                med_spares=core_stock.med_spares + quantity,
            )
        elif job_type == ProductionJobType.WALKERS:
            self.logistics.depot_units[core_id] = UnitStock(
                infantry=core_units.infantry,
                walkers=core_units.walkers + quantity,
                support=core_units.support,
            )
        else:
            raise ValueError(f"Unsupported production job type: {job_type}")

        if output.stop_at != core_id:
            try:
                self.logistics_service.create_shipment(
                    self.logistics,
                    core_id,
                    output.stop_at,
                    supplies,
                    units,
                    self.rng,
                    current_day=self.day,
                )
            except ValueError:
                # Failed to create shipment (e.g. no ship available).
                # Leave goods at Core.
                pass

    def _apply_barracks_output(self, output: BarracksOutput) -> None:
        """Add completed barracks output to Core depot, then auto-dispatch if needed."""
        job_type = output.job_type
        quantity = output.quantity
        core_id = LocationId.NEW_SYSTEM_CORE

        core_units = self.logistics.depot_units[core_id]
        supplies, units = self._build_barracks_payload(job_type, quantity)

        if job_type == BarracksJobType.INFANTRY:
            self.logistics.depot_units[core_id] = UnitStock(
                infantry=core_units.infantry + quantity,
                walkers=core_units.walkers,
                support=core_units.support,
            )
        elif job_type == BarracksJobType.SUPPORT:
            self.logistics.depot_units[core_id] = UnitStock(
                infantry=core_units.infantry,
                walkers=core_units.walkers,
                support=core_units.support + quantity,
            )
        else:
            raise ValueError(f"Unsupported barracks job type: {job_type}")

        if output.stop_at != core_id:
            try:
                self.logistics_service.create_shipment(
                    self.logistics,
                    core_id,
                    output.stop_at,
                    supplies,
                    units,
                    self.rng,
                    current_day=self.day,
                )
            except ValueError:
                pass

    def _build_production_payload(
        self, job_type: ProductionJobType, quantity: int
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
        self, job_type: BarracksJobType, quantity: int
    ) -> tuple[Supplies, UnitStock]:
        if job_type == BarracksJobType.INFANTRY:
            return Supplies(0, 0, 0), UnitStock(infantry=quantity, walkers=0, support=0)
        if job_type == BarracksJobType.SUPPORT:
            return Supplies(0, 0, 0), UnitStock(infantry=0, walkers=0, support=quantity)
        raise ValueError(f"Unsupported barracks job type: {job_type}")

    def _tick_logistics(self) -> None:
        """Advance logistics state by one tick."""
        # Need to update LogisticsService calls too potentially, but let's stick to state access
        # LogisticsService.tick expects 'planet', likely uses 'planet.control' for interdiction?
        # Let's pass contested_planet for now as legacy behavior
        self.logistics_service.tick(self.logistics, self.contested_planet, self.rng, self.day)
        self._sync_task_force_supplies()

    def _resupply_task_force_daily(self) -> None:
        """Resupply task force from key planet depot."""
        self.resupply_task_force()

    def _apply_daily_upkeep(self) -> None:
        """Apply daily fuel/med consumption and readiness degradation."""
        upkeep_fuel = 2
        upkeep_med = 1
        tf_supplies = self.front_supplies
        new_fuel = max(0, tf_supplies.fuel - upkeep_fuel)
        new_med = max(0, tf_supplies.med_spares - upkeep_med)
        self.set_front_supplies(
            Supplies(
                ammo=tf_supplies.ammo,
                fuel=new_fuel,
                med_spares=new_med,
            )
        )
        if new_fuel == 0 or new_med == 0:
            self.task_force.readiness = max(0.0, self.task_force.readiness - 0.02)

    def _apply_enemy_passive_reactions(self) -> None:
        """Apply enemy fortification and force regeneration influenced by reinforcement rate."""
        base_reinforcement_rate = 0.10
        # Access contested planet
        planet = self.contested_planet
        reinforcement_scale = (
            planet.enemy.reinforcement_rate / base_reinforcement_rate
            if base_reinforcement_rate > 0
            else 0.0
        )
        reinforcement_scale = min(2.0, max(0.0, reinforcement_scale))
        enemy = planet.enemy
        if self.operation is None:
            enemy.fortification = min(2.5, enemy.fortification + (0.03 * reinforcement_scale))

            # Regenerate troops between operations (simple MVP rule).
            enemy.infantry = min(5000, enemy.infantry + int(round(5 * reinforcement_scale)))
            if self.rng.random() < (0.05 * reinforcement_scale):
                enemy.walkers = min(200, enemy.walkers + 1)
            if self.rng.random() < (0.07 * reinforcement_scale):
                enemy.support = min(500, enemy.support + 1)

            enemy.cohesion = min(1.0, enemy.cohesion + (0.15 * reinforcement_scale))
        else:
            enemy.fortification = min(2.0, enemy.fortification + (0.01 * reinforcement_scale))
            enemy.cohesion = min(1.0, enemy.cohesion + (0.05 * reinforcement_scale))

    def _apply_storage_loss_events(self) -> None:
        """Apply storage losses that increase with distance from Core."""
        storage_risk_per_day = self.rules.globals.storage_risk_per_day
        storage_loss_pct_range = self.rules.globals.storage_loss_pct_range
        # Iterate over location IDs instead of Enum
        for location_id in self.logistics.depot_stocks.keys():
            risk = storage_risk_per_day.get(location_id, 0.0)
            if risk <= 0:
                continue
            stock = self.logistics.depot_stocks[location_id]
            if stock.ammo == 0 and stock.fuel == 0 and stock.med_spares == 0:
                continue
            if self.rng.random() >= risk:
                continue
            min_loss, max_loss = storage_loss_pct_range.get(location_id, (0.0, 0.0))
            loss_pct = min_loss + (self.rng.random() * (max_loss - min_loss))
            self.logistics.depot_stocks[location_id] = Supplies(
                ammo=max(0, int(stock.ammo * (1 - loss_pct))),
                fuel=max(0, int(stock.fuel * (1 - loss_pct))),
                med_spares=max(0, int(stock.med_spares * (1 - loss_pct))),
            )

    def _progress_operation_if_applicable(self) -> None:
        """Progress operation day if active and not awaiting decision."""
        if self.operation is not None and not self.operation.awaiting_player_decision:
            self.operation.day_in_operation += 1
            self.operation.day_in_phase += 1

            if self.operation.is_phase_complete():
                self._resolve_current_phase()

                if (
                    self.operation is not None
                    and self.operation.decisions.is_complete()
                    and self.operation.auto_advance
                ):
                    self.acknowledge_phase_result()
                    if self.operation is not None:
                        self.operation.awaiting_player_decision = False

    def resupply_task_force(self) -> None:
        caps = Supplies(ammo=300, fuel=200, med_spares=100)
        depot_node = LocationId.CONTESTED_SPACEPORT
        depot_stock = self.logistics.depot_stocks[depot_node]
        depot_units = self.logistics.depot_units[depot_node]
        tf_supplies = self.front_supplies

        ammo_deficit = max(0, caps.ammo - tf_supplies.ammo)
        fuel_deficit = max(0, caps.fuel - tf_supplies.fuel)
        med_deficit = max(0, caps.med_spares - tf_supplies.med_spares)

        ammo_transfer = min(depot_stock.ammo, ammo_deficit)
        fuel_transfer = min(depot_stock.fuel, fuel_deficit)
        med_transfer = min(depot_stock.med_spares, med_deficit)

        transfer_units = depot_units.infantry or depot_units.walkers or depot_units.support
        transfer_supplies = ammo_transfer or fuel_transfer or med_transfer
        if not transfer_units and not transfer_supplies:
            return

        self.logistics.depot_stocks[depot_node] = Supplies(
            ammo=depot_stock.ammo - ammo_transfer,
            fuel=depot_stock.fuel - fuel_transfer,
            med_spares=depot_stock.med_spares - med_transfer,
        )
        if transfer_units:
            self.logistics.depot_units[depot_node] = UnitStock(infantry=0, walkers=0, support=0)
            self.task_force.composition.infantry += depot_units.infantry
            self.task_force.composition.walkers += depot_units.walkers
            self.task_force.composition.support += depot_units.support
        self.set_front_supplies(
            Supplies(
                ammo=tf_supplies.ammo + ammo_transfer,
                fuel=tf_supplies.fuel + fuel_transfer,
                med_spares=tf_supplies.med_spares + med_transfer,
            )
        )

    def start_operation(self, plan: OperationPlan) -> None:
        """Start operation from legacy OperationPlan (backward compatible)."""
        intent = plan.to_intent()
        self.start_operation_phased(intent)
        # Pre-fill all decisions for legacy mode
        self.operation.decisions.phase1 = plan.to_phase1()
        self.operation.decisions.phase2 = plan.to_phase2()
        self.operation.decisions.phase3 = plan.to_phase3()
        # Allow operation to proceed without phase prompts
        self.operation.awaiting_player_decision = False
        self.operation.auto_advance = True

    def start_operation_phased(self, intent: OperationIntent) -> None:
        """Start a new phased operation. Player must submit decisions per phase."""
        if self.operation is not None or self.raid_session is not None:
            raise RuntimeError("Only one active operation allowed")

        # Get operation type config from rules
        op_config = self.rules.operation_types.get(intent.op_type.value)
        if op_config is None:
            base_days = 3
            duration_range = (2, 5)
        else:
            base_days = op_config.base_duration_days
            duration_range = op_config.duration_range

        # Calculate total duration based on enemy state
        fort_mod = max(0, int((self.contested_planet.enemy.fortification - 1.0) * 2))
        control_mod = max(0, int((1.0 - self.contested_planet.control) * 2))
        estimated_days = base_days + fort_mod + control_mod
        estimated_days = max(duration_range[0], min(estimated_days, duration_range[1]))

        # Distribute days across phases
        phase_durations = self._calculate_phase_durations(intent.op_type, estimated_days)

        # Sample enemy strength once for determinism
        enemy = self.contested_planet.enemy
        tf = self.task_force
        enemy_power = calculate_power(
            enemy.infantry,
            enemy.walkers,
            enemy.support,
            cohesion=max(0.0, min(1.0, enemy.cohesion)),
        )
        your_power = calculate_power(
            tf.composition.infantry,
            tf.composition.walkers,
            tf.composition.support,
            cohesion=max(0.0, min(1.0, tf.readiness)),
        )
        raw_ratio = enemy_power / max(1.0, your_power)
        uncertainty = (1.0 - enemy.intel_confidence) * 0.25
        sampled_strength = raw_ratio + self.rng.uniform(-uncertainty, uncertainty)
        sampled_strength = max(0.5, min(2.0, sampled_strength))

        self.operation = ActiveOperation(
            intent=intent,
            estimated_total_days=estimated_days,
            phase_durations=phase_durations,
            phase_start_day=self.day,
            sampled_enemy_strength=sampled_strength,
        )

    def _calculate_phase_durations(
        self, op_type: OperationTypeId, total_days: int
    ) -> dict[OperationPhase, int]:
        """Distribute operation days across phases based on operation type."""
        if op_type == OperationTypeId.RAID:
            # Raids are quick: mostly contact/shaping, short engagement
            return {
                OperationPhase.CONTACT_SHAPING: max(1, total_days // 2),
                OperationPhase.ENGAGEMENT: max(0, total_days - total_days // 2),
                OperationPhase.EXPLOIT_CONSOLIDATE: 0,
            }
        elif op_type == OperationTypeId.SIEGE:
            # Sieges are slow and methodical
            p1 = max(1, total_days // 3)
            p2 = max(1, total_days // 2)
            p3 = max(1, total_days - p1 - p2)
            return {
                OperationPhase.CONTACT_SHAPING: p1,
                OperationPhase.ENGAGEMENT: p2,
                OperationPhase.EXPLOIT_CONSOLIDATE: p3,
            }
        else:  # CAMPAIGN
            # Balanced distribution
            p1 = max(1, total_days // 3)
            p2 = max(1, total_days // 3)
            p3 = max(1, total_days - p1 - p2)
            return {
                OperationPhase.CONTACT_SHAPING: p1,
                OperationPhase.ENGAGEMENT: p2,
                OperationPhase.EXPLOIT_CONSOLIDATE: p3,
            }

    def _operation_supply_multiplier(self, op: ActiveOperation) -> float:
        op_config = self.rules.operation_types.get(op.op_type.value)
        if op_config is None:
            return 1.0
        return op_config.supply_cost_multiplier

    def submit_phase_decisions(
        self, decisions: Phase1Decisions | Phase2Decisions | Phase3Decisions
    ) -> None:
        """Submit decisions for the current phase and allow it to proceed."""
        if self.operation is None:
            raise RuntimeError("No active operation")
        if not self.operation.awaiting_player_decision:
            raise RuntimeError("Not awaiting player decision")

        op = self.operation
        if op.current_phase == OperationPhase.CONTACT_SHAPING:
            if not isinstance(decisions, Phase1Decisions):
                raise TypeError("Expected Phase1Decisions for Contact/Shaping phase")
            op.decisions.phase1 = decisions
        elif op.current_phase == OperationPhase.ENGAGEMENT:
            if not isinstance(decisions, Phase2Decisions):
                raise TypeError("Expected Phase2Decisions for Engagement phase")
            op.decisions.phase2 = decisions
        elif op.current_phase == OperationPhase.EXPLOIT_CONSOLIDATE:
            if not isinstance(decisions, Phase3Decisions):
                raise TypeError("Expected Phase3Decisions for Exploit/Consolidate phase")
            op.decisions.phase3 = decisions
        else:
            raise RuntimeError(f"Cannot submit decisions for phase {op.current_phase}")

        op.awaiting_player_decision = False
        op.phase_start_day = self.day

    def acknowledge_phase_result(self) -> OperationPhaseRecord | None:
        """Acknowledge pending phase result and advance to next phase."""
        if self.operation is None:
            return None
        record = self.operation.pending_phase_record
        if record is None:
            return None

        self.operation.pending_phase_record = None
        self.operation.advance_phase()

        # If operation is complete, finalize AAR
        if self.operation.current_phase == OperationPhase.COMPLETE:
            self._finalize_operation()

        return record

    def _resolve_current_phase(self) -> None:
        """Resolve the current phase and create a phase record."""
        if self.operation is None:
            return

        op = self.operation
        phase = op.current_phase
        events: list[Event] = []

        def log(name: str, value: float, delta: str, why: str) -> None:
            events.append(
                Event(name=name, phase=phase.value, value=value, delta=delta, why=why)
            )

        phase_days = op.current_phase_duration()
        progress_delta = 0.0
        losses = 0
        readiness_delta = 0.0
        supplies_spent = Supplies(ammo=0, fuel=0, med_spares=0)

        if phase == OperationPhase.CONTACT_SHAPING:
            progress_delta, losses, supplies_spent = self._resolve_phase1(op, log)
        elif phase == OperationPhase.ENGAGEMENT:
            progress_delta, losses, supplies_spent = self._resolve_phase2(op, log)
        elif phase == OperationPhase.EXPLOIT_CONSOLIDATE:
            progress_delta, losses, supplies_spent, readiness_delta = (
                self._resolve_phase3(op, log)
            )

        # Consume supplies
        self.set_front_supplies(
            Supplies(
                ammo=max(0, self.front_supplies.ammo - supplies_spent.ammo),
                fuel=max(0, self.front_supplies.fuel - supplies_spent.fuel),
                med_spares=max(0, self.front_supplies.med_spares - supplies_spent.med_spares),
            )
        )

        # Apply losses
        self._apply_losses(losses)

        # Update accumulated values
        op.accumulated_progress += progress_delta
        op.accumulated_losses += losses

        # Update readiness
        self.task_force.readiness = min(1.0, max(0.0, self.task_force.readiness + readiness_delta))

        summary = PhaseSummary(
            progress_delta=progress_delta,
            losses=losses,
            supplies_spent=supplies_spent,
            readiness_delta=readiness_delta,
        )

        # Get decisions for this phase
        if phase == OperationPhase.CONTACT_SHAPING:
            decisions = op.decisions.phase1
        elif phase == OperationPhase.ENGAGEMENT:
            decisions = op.decisions.phase2
        else:
            decisions = op.decisions.phase3

        record = OperationPhaseRecord(
            phase=phase,
            start_day=op.phase_start_day,
            end_day=self.day,
            decisions=decisions,
            summary=summary,
            events=events,
        )

        op.phase_history.append(record)
        op.pending_phase_record = record
        op.awaiting_player_decision = True

    def _resolve_phase1(
        self, op: ActiveOperation, log
    ) -> tuple[float, int, Supplies]:
        """Resolve Contact & Shaping phase."""
        d = op.decisions.phase1
        if d is None:
            return 0.0, 0, Supplies(0, 0, 0)

        phase_days = op.phase_durations.get(OperationPhase.CONTACT_SHAPING, 1)

        approach_rules = self.rules.approach_axes.get(
            d.approach_axis, {"progress_mod": 0.0, "loss_mod": 0.0}
        )
        prep_rules = self.rules.fire_support_prep.get(
            d.fire_support_prep, {"progress_mod": 0.0, "loss_mod": 0.0}
        )

        base_progress = self._phase_base_progress(op, OperationPhase.CONTACT_SHAPING, phase_days)
        progress = base_progress + approach_rules.get("progress_mod", 0.0) + prep_rules.get("progress_mod", 0.0)
        loss_mod = approach_rules.get("loss_mod", 0.0) + prep_rules.get("loss_mod", 0.0)

        log("base_progress", base_progress, "progress", "Base progress from contact & shaping tempo")
        log(
            f"approach_{d.approach_axis}",
            approach_rules.get("progress_mod", 0.0),
            "progress",
            f"Approach: {d.approach_axis}",
        )
        log(f"fire_support_{d.fire_support_prep}", prep_rules.get("progress_mod", 0.0), "progress", f"Fire support: {d.fire_support_prep}")

        # Enemy factors affect phase 1
        strength_penalty = -0.10 * (op.sampled_enemy_strength - 1.0)
        control_penalty = -0.08 * (1.0 - self.contested_planet.control)
        progress += strength_penalty + control_penalty

        log("enemy_strength", strength_penalty, "progress", f"Enemy strength {op.sampled_enemy_strength:.2f}")
        log("planet_control", control_penalty, "progress", f"Control level {self.contested_planet.control:.2f}")

        # Supply costs for this phase
        base_ammo = 15 + (5 if d.fire_support_prep == "preparatory" else 0)
        base_fuel = 10 + (5 if d.approach_axis == "flank" else 0)
        supply_mult = self._operation_supply_multiplier(op)
        ammo_cost = int(round(base_ammo * phase_days * supply_mult))
        fuel_cost = int(round(base_fuel * phase_days * supply_mult))

        # Check for shortages
        if self.front_supplies.ammo < ammo_cost:
            ammo_class = self.rules.supply_classes.get("ammo")
            if ammo_class:
                penalty = ammo_class.shortage_effects.get("progress_penalty", -0.30)
                progress += penalty
                log("ammo_shortage", penalty, "progress", "Insufficient ammo reduces shaping effectiveness")

        supplies_spent = Supplies(ammo=ammo_cost, fuel=fuel_cost, med_spares=0)

        # Calculate losses (light in phase 1)
        total_units = (
            self.task_force.composition.infantry
            + self.task_force.composition.walkers
            + self.task_force.composition.support
        )
        losses = int(max(0, (0.03 + loss_mod) * total_units * phase_days))

        return progress, losses, supplies_spent

    def _resolve_phase2(
        self, op: ActiveOperation, log
    ) -> tuple[float, int, Supplies]:
        """Resolve Main Engagement phase."""
        d = op.decisions.phase2
        if d is None:
            return 0.0, 0, Supplies(0, 0, 0)

        phase_days = op.phase_durations.get(OperationPhase.ENGAGEMENT, 1)

        posture_rules = self.rules.engagement_postures.get(
            d.engagement_posture, {"progress_mod": 0.0, "loss_mod": 0.0}
        )
        risk_rules = self.rules.risk_tolerances.get(
            d.risk_tolerance, {"progress_mod": 0.0, "loss_mod": 0.0, "variance_multiplier": 1.0}
        )

        base_progress = self._phase_base_progress(op, OperationPhase.ENGAGEMENT, phase_days)
        progress = base_progress + posture_rules.get("progress_mod", 0.0) + risk_rules.get("progress_mod", 0.0)
        loss_mod = posture_rules.get("loss_mod", 0.0) + risk_rules.get("loss_mod", 0.0)
        variance_mult = risk_rules.get("variance_multiplier", 1.0)

        log("base_progress", base_progress, "progress", "Base progress from main engagement tempo")
        log(f"posture_{d.engagement_posture}", posture_rules.get("progress_mod", 0.0), "progress", f"Posture: {d.engagement_posture}")
        log(f"risk_{d.risk_tolerance}", risk_rules.get("progress_mod", 0.0), "progress", f"Risk tolerance: {d.risk_tolerance}")

        # Fortification is main factor in engagement
        fort = self.contested_planet.enemy.fortification
        fort_penalty = -0.15 * (fort - 1.0)
        progress += fort_penalty
        log("enemy_fortification", fort_penalty, "progress", f"Fortification {fort:.2f} resists assault")

        # Preparatory fires from Phase 1 soften defenses
        if op.decisions.phase1 and op.decisions.phase1.fire_support_prep == "preparatory":
            prep_bonus = 0.05 * max(0.0, fort - 1.0)
            if prep_bonus > 0:
                progress += prep_bonus
                log("preparatory_bombardment", prep_bonus, "progress", "Preparatory fires weaken fortifications")

        # Variance from intel confidence
        support_role = self.rules.unit_roles.get("support")
        recon_reduction = 0.0
        if support_role and support_role.recon:
            recon_rating = self.task_force.composition.support * support_role.recon.get("variance_reduction", 0.30) / 10.0
            recon_reduction = min(0.5, recon_rating)
        phase1_recon = 0.0
        if op.decisions.phase1:
            axis = op.decisions.phase1.approach_axis
            if axis == "stealth":
                phase1_recon = 0.10
            elif axis == "dispersed":
                phase1_recon = 0.05
        if phase1_recon > 0.0:
            recon_reduction = min(0.6, recon_reduction + phase1_recon)
        base_variance = 0.20 * (1.0 - self.contested_planet.enemy.intel_confidence) * variance_mult
        variance = base_variance * (1.0 - recon_reduction)
        noise = self.rng.uniform(-variance, variance)
        progress += noise
        log(
            "fog_of_war",
            noise,
            "progress",
            f"Combat variance (intel {int(self.contested_planet.enemy.intel_confidence * 100)}%)",
        )
        if recon_reduction > 0.01:
            log("recon_variance_reduction", -base_variance * recon_reduction, "progress", f"Recon units reduce variance by {int(recon_reduction * 100)}%")

        # Clone morale vs droid stability
        morale = 0.6 * self.task_force.cohesion + 0.4 * self.task_force.readiness
        morale_roll = self.rng.uniform(-0.03, 0.03)
        morale_shift = (morale - 0.5) * 0.10 + morale_roll
        progress += morale_shift
        log("clone_morale", morale_shift, "progress", f"Morale {morale:.2f} drives momentum")
        morale_loss_mod = 0.0
        if morale < 0.4:
            morale_loss_mod = 0.03
        elif morale > 0.7:
            morale_loss_mod = -0.02
        if morale_loss_mod != 0.0:
            loss_mod += morale_loss_mod
            log("clone_morale_losses", morale_loss_mod, "losses", "Morale swing affects casualty rate")

        enemy_stability = self.contested_planet.enemy.cohesion
        stability_penalty = -0.06 * (enemy_stability - 0.5)
        progress += stability_penalty
        log("enemy_stability", stability_penalty, "progress", f"Enemy stability {enemy_stability:.2f} resists disruption")

        # Supply costs
        supply_mult = self._operation_supply_multiplier(op)
        ammo_cost = int(round(25 * phase_days * supply_mult))
        fuel_cost = int(round(15 * phase_days * supply_mult))
        med_cost = int(round(5 * phase_days * supply_mult))

        if self.front_supplies.fuel < fuel_cost:
            fuel_class = self.rules.supply_classes.get("fuel")
            if fuel_class:
                penalty = fuel_class.shortage_effects.get("progress_penalty", -0.30)
                progress += penalty
                log("fuel_shortage", penalty, "progress", "Insufficient fuel slows maneuver")

        supplies_spent = Supplies(ammo=ammo_cost, fuel=fuel_cost, med_spares=med_cost)

        # Signature interactions for losses
        walker_role = self.rules.unit_roles.get("walkers")
        infantry_role = self.rules.unit_roles.get("infantry")
        protection_reduction = 0.0
        if walker_role and walker_role.transport_protection and infantry_role:
            walker_count = self.task_force.composition.walkers
            infantry_count = self.task_force.composition.infantry
            capacity_per_walker = walker_role.transport_protection.get("protection_capacity", 3)
            max_protected = min(infantry_count, walker_count * capacity_per_walker)
            if max_protected > 0:
                protection_factor = max_protected / max(1, infantry_count)
                protection_reduction = protection_factor * infantry_role.transport_protection.get("protection_reduction", 0.40)
                log("transport_protection", -protection_reduction, "losses", f"Walkers protect {max_protected} troopers")

        # Calculate losses (heaviest in phase 2)
        total_units = (
            self.task_force.composition.infantry
            + self.task_force.composition.walkers
            + self.task_force.composition.support
        )
        base_loss_rate = 0.08 + 0.06 * max(0, fort - 1.0) + 0.04 * max(0, op.sampled_enemy_strength - 1.0)
        losses_rate = base_loss_rate + loss_mod - protection_reduction
        losses = int(max(0, losses_rate * total_units * phase_days))

        return progress, losses, supplies_spent

    def _resolve_phase3(
        self, op: ActiveOperation, log
    ) -> tuple[float, int, Supplies, float]:
        """Resolve Exploit & Consolidate phase."""
        d = op.decisions.phase3
        if d is None:
            return 0.0, 0, Supplies(0, 0, 0), 0.0

        phase_days = op.phase_durations.get(OperationPhase.EXPLOIT_CONSOLIDATE, 1)
        if phase_days == 0:
            # Raids skip phase 3
            return 0.0, 0, Supplies(0, 0, 0), 0.0

        exploit_rules = self.rules.exploit_vs_secure.get(
            d.exploit_vs_secure, {"progress_mod": 0.0, "loss_mod": 0.0}
        )
        end_state_rules = self.rules.end_states.get(
            d.end_state, {"required_progress": 0.75, "fortification_reduction": 0.0, "reinforcement_reduction": 0.0}
        )

        base_progress = self._phase_base_progress(op, OperationPhase.EXPLOIT_CONSOLIDATE, phase_days)
        progress = base_progress + exploit_rules.get("progress_mod", 0.0)
        loss_mod = exploit_rules.get("loss_mod", 0.0)

        log("base_progress", base_progress, "progress", "Base progress from exploitation tempo")
        log(
            f"exploit_{d.exploit_vs_secure}",
            exploit_rules.get("progress_mod", 0.0),
            "progress",
            f"Exploit vs Secure: {d.exploit_vs_secure}",
        )
        log(f"end_state_{d.end_state}", 0.0, "objective", f"End state: {d.end_state}")

        # Medic sustainment
        support_role = self.rules.unit_roles.get("support")
        medic_reduction = 0.0
        readiness_delta = 0.0
        if support_role and support_role.sustainment:
            medic_count = self.task_force.composition.support
            casualty_red = support_role.sustainment.get("casualty_reduction", 0.25)
            readiness_rec = support_role.sustainment.get("readiness_recovery", 0.15)
            medic_reduction = (medic_count / 10.0) * casualty_red
            readiness_delta = (medic_count / 10.0) * readiness_rec
            if medic_reduction > 0.01:
                log("medic_sustainment", -medic_reduction, "losses", f"Medics reduce casualties")
            if readiness_delta > 0.01:
                log("medic_readiness", readiness_delta, "readiness", f"Medics improve recovery")

        # Supply costs
        supply_mult = self._operation_supply_multiplier(op)
        med_cost = int(round(8 * phase_days * supply_mult))
        supplies_spent = Supplies(
            ammo=int(round(5 * phase_days * supply_mult)),
            fuel=int(round(5 * phase_days * supply_mult)),
            med_spares=med_cost,
        )

        if self.front_supplies.med_spares < med_cost:
            med_class = self.rules.supply_classes.get("med_spares")
            if med_class:
                penalty = med_class.shortage_effects.get("loss_multiplier", 1.20)
                loss_mod += (penalty - 1.0) * 0.05
                log("med_spares_shortage", (penalty - 1.0) * 0.05, "losses", "Insufficient med/spares increases casualties")

        # Lighter losses in consolidation
        total_units = (
            self.task_force.composition.infantry
            + self.task_force.composition.walkers
            + self.task_force.composition.support
        )
        losses_rate = 0.03 + loss_mod - medic_reduction
        losses = int(max(0, losses_rate * total_units * phase_days))

        return progress, losses, supplies_spent, readiness_delta

    def _apply_losses(self, losses: int) -> None:
        """Apply unit losses to task force composition."""
        if losses <= 0:
            return

        total_units = (
            self.task_force.composition.infantry
            + self.task_force.composition.walkers
            + self.task_force.composition.support
        )
        if total_units == 0:
            return

        losses = min(losses, total_units)

        infantry = self.task_force.composition.infantry
        walkers = self.task_force.composition.walkers
        support = self.task_force.composition.support

        # Distribute losses (infantry takes more), then reallocate any remainder to available units.
        infantry_losses = min(infantry, int(losses * 0.6))
        walker_losses = min(walkers, int(losses * 0.3))
        support_losses = min(support, int(losses * 0.1))
        remaining = losses - (infantry_losses + walker_losses + support_losses)

        if remaining > 0:
            add = min(infantry - infantry_losses, remaining)
            infantry_losses += add
            remaining -= add
        if remaining > 0:
            add = min(walkers - walker_losses, remaining)
            walker_losses += add
            remaining -= add
        if remaining > 0:
            add = min(support - support_losses, remaining)
            support_losses += add
            remaining -= add

        self.task_force.composition.infantry = max(0, infantry - infantry_losses)
        self.task_force.composition.walkers = max(0, walkers - walker_losses)
        self.task_force.composition.support = max(0, support - support_losses)

        # Heavy losses reduce readiness
        if losses > total_units * 0.1:
            self.task_force.readiness = max(0.5, self.task_force.readiness - 0.1)

    @staticmethod
    def _phase_base_progress(
        op: ActiveOperation,
        phase: OperationPhase,
        phase_days: int,
    ) -> float:
        if phase_days <= 0 or op.estimated_total_days <= 0:
            return 0.0
        return phase_days / op.estimated_total_days

    def _finalize_operation(self) -> None:
        """Finalize operation and create AAR after all phases complete."""
        if self.operation is None:
            return

        op = self.operation
        d3 = op.decisions.phase3

        # Flatten all events from phase history
        all_events: list[Event] = []
        for record in op.phase_history:
            all_events.extend(record.events)

        # Determine success
        end_state = d3.end_state if d3 else "withdraw"
        end_state_rules = self.rules.end_states.get(
            end_state, {"required_progress": 0.75, "fortification_reduction": 0.0, "reinforcement_reduction": 0.0}
        )
        required_progress = end_state_rules.get("required_progress", 0.75)
        success = op.accumulated_progress >= required_progress

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

        # Apply consequences
        if success:
            fort_reduction = end_state_rules.get("fortification_reduction", 0.0)
            reinf_reduction = end_state_rules.get("reinforcement_reduction", 0.0)
            if end_state == "capture":
                self._set_objective(op.target, ObjectiveStatus.SECURED)
            if end_state == "capture":
                self._set_objective(op.target, ObjectiveStatus.SECURED)
                self.contested_planet.control = min(1.0, self.contested_planet.control + 0.15)
                self.contested_planet.enemy.fortification = max(0.6, self.contested_planet.enemy.fortification - fort_reduction)
                self.contested_planet.enemy.reinforcement_rate = max(0.0, self.contested_planet.enemy.reinforcement_rate - reinf_reduction)
            elif end_state == "raid":
                self.contested_planet.control = min(1.0, self.contested_planet.control + 0.05)
                self.contested_planet.enemy.reinforcement_rate = max(0.0, self.contested_planet.enemy.reinforcement_rate - reinf_reduction)
            elif end_state == "destroy":
                self.contested_planet.control = min(1.0, self.contested_planet.control + 0.10)
                self.contested_planet.enemy.fortification = max(0.6, self.contested_planet.enemy.fortification - fort_reduction)
                self.contested_planet.enemy.reinforcement_rate = max(0.0, self.contested_planet.enemy.reinforcement_rate - reinf_reduction)
        elif end_state != "withdraw":
            self.contested_planet.control = max(0.0, self.contested_planet.control - 0.10)
            self.contested_planet.enemy.fortification = min(2.5, self.contested_planet.enemy.fortification + 0.10)

        self._update_intel_confidence(op, success)

        top = self._top_factors(all_events)
        self.last_aar = AfterActionReport(
            outcome=outcome,
            target=op.target,
            operation_type=op.op_type.value,
            days=op.day_in_operation,
            losses=op.accumulated_losses,
            remaining_supplies=self.front_supplies,
            top_factors=top,
            phases=list(op.phase_history),
            events=all_events,
        )
        self.operation = None

    def resolve_operation(self) -> None:
        """Legacy: Resolve active operation all at once (for backward compatibility)."""
        if self.operation is None:
            raise RuntimeError("No active operation")

        op = self.operation
        events: list[Event] = []

        def log(name: str, phase: str, value: float, delta: str, why: str) -> None:
            events.append(Event(name=name, phase=phase, value=value, delta=delta, why=why))

        # Build a legacy-style plan from decisions
        d1 = op.decisions.phase1
        d2 = op.decisions.phase2
        d3 = op.decisions.phase3
        
        if d1 is None or d2 is None or d3 is None:
            raise RuntimeError("Cannot resolve operation without all phase decisions")
        
        days = op.day_in_operation if op.day_in_operation > 0 else op.estimated_total_days

        # Calculate supply costs (per day, multiplied by duration)
        base_ammo_per_day = 20
        base_fuel_per_day = 15
        base_med_per_day = 5
        ammo_cost = int((base_ammo_per_day + (5 if d1.fire_support_prep == "preparatory" else 0)) * days)
        fuel_cost = int((base_fuel_per_day + (5 if d1.approach_axis == "flank" else 0)) * days)
        med_cost = int(base_med_per_day * days)

        # Get rules
        approach_rules = self.rules.approach_axes.get(d1.approach_axis, {"progress_mod": 0.0, "loss_mod": 0.0})
        prep_rules = self.rules.fire_support_prep.get(d1.fire_support_prep, {"progress_mod": 0.0, "loss_mod": 0.0})
        posture_rules = self.rules.engagement_postures.get(d2.engagement_posture, {"progress_mod": 0.0, "loss_mod": 0.0})
        risk_rules = self.rules.risk_tolerances.get(d2.risk_tolerance, {"progress_mod": 0.0, "loss_mod": 0.0, "variance_multiplier": 1.0})
        exploit_rules = self.rules.exploit_vs_secure.get(d3.exploit_vs_secure, {"progress_mod": 0.0, "loss_mod": 0.0})
        end_state_rules = self.rules.end_states.get(d3.end_state, {"required_progress": 0.75, "fortification_reduction": 0.0, "reinforcement_reduction": 0.0})

        progress_mod = 0.0
        loss_mod = 0.0

        # Phase 1: Contact & Shaping
        app_progress = approach_rules.get("progress_mod", 0.0)
        app_loss = approach_rules.get("loss_mod", 0.0)
        progress_mod += app_progress
        loss_mod += app_loss
        log("approach_axis", "Phase 1", app_progress, "progress", f"Approach {d1.approach_axis}")
        log("approach_axis", "Phase 1", app_loss, "losses", f"Approach {d1.approach_axis}")

        prep_progress = prep_rules.get("progress_mod", 0.0)
        prep_loss = prep_rules.get("loss_mod", 0.0)
        progress_mod += prep_progress
        loss_mod += prep_loss
        log("fire_support_prep", "Phase 1", prep_progress, "progress", f"Fire support {d1.fire_support_prep}")
        log("fire_support_prep", "Phase 1", prep_loss, "losses", f"Fire support {d1.fire_support_prep}")

        # Phase 2: Main Engagement
        posture_progress = posture_rules.get("progress_mod", 0.0)
        posture_loss = posture_rules.get("loss_mod", 0.0)
        progress_mod += posture_progress
        loss_mod += posture_loss
        log("engagement_posture", "Phase 2", posture_progress, "progress", f"Posture {d2.engagement_posture}")
        log("engagement_posture", "Phase 2", posture_loss, "losses", f"Posture {d2.engagement_posture}")

        risk_progress = risk_rules.get("progress_mod", 0.0)
        risk_loss = risk_rules.get("loss_mod", 0.0)
        variance_mult = risk_rules.get("variance_multiplier", 1.0)
        progress_mod += risk_progress
        loss_mod += risk_loss
        log("risk_tolerance", "Phase 2", risk_progress, "progress", f"Risk {d2.risk_tolerance}")
        log("risk_tolerance", "Phase 2", risk_loss, "losses", f"Risk {d2.risk_tolerance}")

        # Phase 3: Exploit & Consolidate
        exploit_progress = exploit_rules.get("progress_mod", 0.0)
        exploit_loss = exploit_rules.get("loss_mod", 0.0)
        progress_mod += exploit_progress
        loss_mod += exploit_loss
        log("exploit_vs_secure", "Phase 3", exploit_progress, "progress", f"Exploit {d3.exploit_vs_secure}")
        log("exploit_vs_secure", "Phase 3", exploit_loss, "losses", f"Exploit {d3.exploit_vs_secure}")

        # Supply shortages
        shortages = 0
        supply_shortage_penalty = 0.0
        if self.front_supplies.ammo < ammo_cost:
            shortages += 1
            ammo_class = self.rules.supply_classes.get("ammo")
            if ammo_class:
                penalty = ammo_class.shortage_effects.get("progress_penalty", -0.30)
                supply_shortage_penalty += penalty
                log("ammo_shortage", "Phase 1", penalty, "progress", "Insufficient ammo reduces shaping effectiveness")
        if self.front_supplies.fuel < fuel_cost:
            shortages += 1
            fuel_class = self.rules.supply_classes.get("fuel")
            if fuel_class:
                penalty = fuel_class.shortage_effects.get("progress_penalty", -0.30)
                supply_shortage_penalty += penalty
                log("fuel_shortage", "Phase 2", penalty, "progress", "Insufficient fuel slows maneuver")
        if self.front_supplies.med_spares < med_cost:
            shortages += 1
            med_class = self.rules.supply_classes.get("med_spares")
            if med_class:
                penalty = med_class.shortage_effects.get("loss_multiplier", 1.20)
                loss_mod += (penalty - 1.0) * 0.1  # Convert multiplier to additive
                log("med_spares_shortage", "Phase 3", (penalty - 1.0) * 0.1, "losses", "Insufficient med/spares increases casualties")

        # Enemy factors
        base_progress = 1.0
        fort = self.contested_planet.enemy.fortification
        fort_penalty = -0.25 * (fort - 1.0)
        log("enemy_fortification", "Phase 2", fort_penalty, "progress", f"Fortification {fort:.2f} resists assault")

        enemy_strength = self.rng.uniform(
            0.8,
            1.2,
        )
        strength_penalty = -0.20 * (enemy_strength - 1.0)
        log("enemy_strength", "Phase 1", strength_penalty, "progress", f"Enemy strength {enemy_strength:.2f}")

        # Planet control effect (lower control = harder)
        control_penalty = -0.15 * (1.0 - self.contested_planet.control)
        log("planet_control", "Phase 1", control_penalty, "progress", f"Control level {self.contested_planet.control:.2f} affects operations")

        # Signature Interaction 1: Recon reduces variance
        # Calculate recon rating from support units
        support_role = self.rules.unit_roles.get("support")
        recon_reduction = 0.0
        if support_role and support_role.recon:
            recon_rating = self.task_force.composition.support * support_role.recon.get("variance_reduction", 0.30) / 10.0
            recon_reduction = min(0.5, recon_rating)  # Cap at 50% reduction
        base_variance = 0.25 * (1.0 - self.planet.enemy.intel_confidence) * variance_mult
        variance = base_variance * (1.0 - recon_reduction)
        noise = self.rng.uniform(-variance, variance)
        log(
            "fog_of_war",
            "Phase 2",
            noise,
            "progress",
            f"Variance from intel ({int(self.planet.enemy.intel_confidence * 100)}%) and recon",
        )
        if recon_reduction > 0.01:
            log("recon_variance_reduction", "Phase 2", -base_variance * recon_reduction, "progress", f"Recon units reduce variance by {int(recon_reduction * 100)}%")

        # Calculate progress
        progress = (
            base_progress
            + fort_penalty
            + strength_penalty
            + control_penalty
            + progress_mod
            + noise
            + supply_shortage_penalty
        )

        # Signature Interaction 2: Transport/protection (walkers protect infantry)
        walker_role = self.rules.unit_roles.get("walkers")
        infantry_role = self.rules.unit_roles.get("infantry")
        protection_reduction = 0.0
        if walker_role and walker_role.transport_protection and infantry_role:
            walker_count = self.task_force.composition.walkers
            infantry_count = self.task_force.composition.infantry
            capacity_per_walker = walker_role.transport_protection.get("protection_capacity", 3)
            max_protected = min(infantry_count, walker_count * capacity_per_walker)
            if max_protected > 0:
                protection_factor = max_protected / max(1, infantry_count)
                protection_reduction = protection_factor * infantry_role.transport_protection.get("protection_reduction", 0.40)
                # Check if walkers are degraded (simplified: if losses would be high)
                degradation_threshold = walker_role.transport_protection.get("degradation_threshold", 0.5)
                if walker_count < degradation_threshold * 2:  # Simplified check
                    protection_reduction *= 0.5
                    log("walker_degradation", "Phase 2", 0.0, "losses", "Walker effectiveness degraded")
                log("transport_protection", "Phase 2", -protection_reduction, "losses", f"Walkers protect {max_protected} infantry units")

        # Signature Interaction 3: Medics improve sustainment
        medic_reduction = 0.0
        medic_readiness = 0.0
        if support_role and support_role.sustainment:
            medic_count = self.task_force.composition.support
            casualty_red = support_role.sustainment.get("casualty_reduction", 0.25)
            readiness_rec = support_role.sustainment.get("readiness_recovery", 0.15)
            medic_reduction = (medic_count / 10.0) * casualty_red  # Scale by medic count
            medic_readiness = (medic_count / 10.0) * readiness_rec
            if medic_reduction > 0.01:
                log("medic_sustainment", "Phase 2", -medic_reduction, "losses", f"Medics reduce casualties by {int(medic_reduction * 100)}%")
            if medic_readiness > 0.01:
                log("medic_readiness", "Phase 3", medic_readiness, "readiness", f"Medics improve readiness recovery")

        # Calculate losses
        base_losses_rate = 0.08
        losses_rate = (
            base_losses_rate
            + 0.08 * max(0.0, fort - 1.0)
            + 0.05 * max(0.0, enemy_strength - 1.0)
            + loss_mod
            + 0.05 * shortages
            - protection_reduction  # Apply protection
            - medic_reduction  # Apply medic reduction
        )
        losses = int(max(0.0, losses_rate * 100 * days))  # Scale by days
        log("casualty_pressure", "Phase 2", float(losses), "losses", "Casualties driven by fortification, strength, posture, and interactions")

        # Apply losses to composition (simplified: reduce infantry first, then others)
        total_units = self.task_force.composition.infantry + self.task_force.composition.walkers + self.task_force.composition.support
        if losses > 0 and total_units > 0:
            # Distribute losses (infantry takes more)
            infantry_losses = min(self.task_force.composition.infantry, int(losses * 0.6))
            walker_losses = min(self.task_force.composition.walkers, int(losses * 0.3))
            support_losses = min(self.task_force.composition.support, int(losses * 0.1))
            self.task_force.composition.infantry = max(0, self.task_force.composition.infantry - infantry_losses)
            self.task_force.composition.walkers = max(0, self.task_force.composition.walkers - walker_losses)
            self.task_force.composition.support = max(0, self.task_force.composition.support - support_losses)

        # Update readiness (medics help)
        self.task_force.readiness = min(1.0, self.task_force.readiness + medic_readiness)
        if losses > total_units * 0.1:  # Heavy losses reduce readiness
            self.task_force.readiness = max(0.5, self.task_force.readiness - 0.1)

        # Determine success
        required_progress = end_state_rules.get("required_progress", 0.75)
        success = progress >= required_progress
        outcome_map = {
            "capture": "CAPTURED",
            "raid": "RAIDED",
            "destroy": "DESTROYED",
            "withdraw": "WITHDREW",
        }
        if d3.end_state == "withdraw":
            outcome = outcome_map["withdraw"]
            success = False
        else:
            outcome = outcome_map[d3.end_state] if success else "FAILED"

        # Consume supplies
        self.set_front_supplies(
            Supplies(
                ammo=max(0, self.front_supplies.ammo - ammo_cost),
                fuel=max(0, self.front_supplies.fuel - fuel_cost),
                med_spares=max(0, self.front_supplies.med_spares - med_cost),
            )
        )

        # Apply consequences
        if success:
            fort_reduction = end_state_rules.get("fortification_reduction", 0.0)
            reinf_reduction = end_state_rules.get("reinforcement_reduction", 0.0)
            if d3.end_state == "capture":
                self._set_objective(op.target, ObjectiveStatus.SECURED)
                self.planet.control = min(1.0, self.planet.control + 0.15)
                self.planet.enemy.fortification = max(0.6, self.planet.enemy.fortification - fort_reduction)
                self.planet.enemy.reinforcement_rate = max(0.0, self.planet.enemy.reinforcement_rate - reinf_reduction)
                log("objective_secured", "Phase 3", +1.0, "objective", "Objective secured; enemy effects reduced, control increased")
            elif d3.end_state == "raid":
                self.planet.control = min(1.0, self.planet.control + 0.05)
                self.planet.enemy.reinforcement_rate = max(0.0, self.planet.enemy.reinforcement_rate - reinf_reduction)
                log("objective_raided", "Phase 3", +0.6, "objective", "Raid disrupts reinforcement flow")
            elif d3.end_state == "destroy":
                self.planet.control = min(1.0, self.planet.control + 0.10)
                self.planet.enemy.fortification = max(0.6, self.planet.enemy.fortification - fort_reduction)
                self.planet.enemy.reinforcement_rate = max(0.0, self.planet.enemy.reinforcement_rate - reinf_reduction)
                log("objective_destroyed", "Phase 3", +0.8, "objective", "Destruction weakens defenses")
        elif d3.end_state != "withdraw":
            # Failure consequences: lose control, increase fortification
            self.planet.control = max(0.0, self.planet.control - 0.10)
            self.planet.enemy.fortification = min(2.5, self.planet.enemy.fortification + 0.10)
            log("operation_failed", "Phase 3", -1.0, "objective", "Failure increases enemy fortification and reduces control")

        top = self._top_factors(events)
        self.last_aar = AfterActionReport(
            outcome=outcome,
            target=op.target,
            operation_type=op.op_type.value,
            days=days,
            losses=losses,
            remaining_supplies=self.front_supplies,
            top_factors=top,
            phases=list(op.phase_history),
            events=events,
        )
        self.operation = None

    def _get_objective_status(self, target: OperationTarget) -> ObjectiveStatus:
        if target == OperationTarget.FOUNDRY:
            return self.contested_planet.objectives.foundry
        elif target == OperationTarget.COMMS:
            return self.contested_planet.objectives.comms
        else:
            return self.contested_planet.objectives.power

    def _set_objective(self, target: OperationTarget, status: ObjectiveStatus) -> None:
        if target == OperationTarget.FOUNDRY:
            self.contested_planet.objectives.foundry = status
        elif target == OperationTarget.COMMS:
            self.contested_planet.objectives.comms = status
        elif target == OperationTarget.POWER:
            self.contested_planet.objectives.power = status

    @staticmethod
    def _top_factors(events: list[Event]) -> list[TopFactor]:
        scored: list[tuple[float, Event]] = []
        for ev in events:
            score = abs(ev.value)
            scored.append((score, ev))
        scored.sort(key=lambda t: t[0], reverse=True)
        top: list[TopFactor] = []
        for _, ev in scored[:5]:
            top.append(TopFactor(name=ev.name, value=ev.value, delta=ev.delta, why=ev.why))
        return top

    def _update_intel_confidence(self, op: ActiveOperation, success: bool) -> None:
        enemy = self.contested_planet.enemy
        gain = 0.02
        if op.decisions.phase1:
            axis = op.decisions.phase1.approach_axis
            if axis == "stealth":
                gain += 0.03
            elif axis == "dispersed":
                gain += 0.02
        support_role = self.rules.unit_roles.get("support")
        if support_role and support_role.recon:
            recon_gain = min(0.05, self.task_force.composition.support * 0.005)
            gain += recon_gain
        if success:
            gain += 0.02
        enemy.intel_confidence = min(0.95, max(0.05, enemy.intel_confidence + gain))
