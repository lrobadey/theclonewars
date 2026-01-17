from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from random import Random

from clone_wars.engine.logging import Event, TopFactor
from clone_wars.engine.logistics import (
    DepotNode,
    LogisticsState,
    STORAGE_LOSS_PCT_RANGE,
    STORAGE_RISK_PER_DAY,
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
from clone_wars.engine.production import ProductionJobType, ProductionOutput, ProductionState
from clone_wars.engine.rules import Ruleset, RulesError
from clone_wars.engine.services.logistics import LogisticsService
from clone_wars.engine.types import ObjectiveStatus, Supplies, UnitStock


@dataclass(slots=True)
class Objectives:
    foundry: ObjectiveStatus
    comms: ObjectiveStatus
    power: ObjectiveStatus


@dataclass(slots=True)
class EnemyPackage:
    strength_min: float
    strength_max: float
    confidence: float
    fortification: float
    reinforcement_rate: float


@dataclass(slots=True)
class PlanetState:
    objectives: Objectives
    enemy: EnemyPackage
    control: float  # 0.0 to 1.0, player control level


# ProductionState moved to production.py module


@dataclass(slots=True)
class UnitComposition:
    infantry: int
    walkers: int
    support: int


@dataclass(slots=True)
class TaskForceState:
    composition: UnitComposition
    readiness: float
    cohesion: float
    supplies: Supplies


@dataclass(frozen=True, slots=True)
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


@dataclass(slots=True)
class GameState:
    day: int
    rng_seed: int
    rng: Random

    planet: PlanetState
    production: ProductionState
    logistics: LogisticsState
    task_force: TaskForceState
    rules: Ruleset
    logistics_service: LogisticsService = field(default_factory=LogisticsService, init=False)

    operation: ActiveOperation | None
    last_aar: AfterActionReport | None

    @staticmethod
    def new(seed: int = 1, data_dir: Path | None = None) -> "GameState":
        rng = Random(seed)
        if data_dir is None:
            data_dir = Path(__file__).resolve().parents[1] / "data"
        try:
            rules = Ruleset.load(data_dir)
        except RulesError as exc:
            raise RuntimeError(f"Failed to load rules: {exc}") from exc

        return GameState(
            day=1,
            rng_seed=seed,
            rng=rng,
            planet=PlanetState(
                objectives=Objectives(
                    foundry=ObjectiveStatus.ENEMY,
                    comms=ObjectiveStatus.ENEMY,
                    power=ObjectiveStatus.ENEMY,
                ),
                enemy=EnemyPackage(
                    strength_min=1.2,
                    strength_max=2.0,
                    confidence=0.70,
                    fortification=1.00,
                    reinforcement_rate=0.10,
                ),
                control=0.3,  # Initial control level
            ),
            production=ProductionState.new(capacity=3),
            logistics=LogisticsState.new(),
            task_force=TaskForceState(
                composition=UnitComposition(infantry=6, walkers=2, support=1),
                readiness=1.00,
                cohesion=1.00,
                supplies=Supplies(ammo=120, fuel=90, med_spares=40),
            ),
            rules=rules,
            operation=None,
            last_aar=None,
        )

    def advance_day(self) -> None:
        """Advance game state by one day."""
        self.day += 1
        self._tick_production_and_distribute_to_core()
        self._tick_logistics()
        self._resupply_task_force_daily()
        self._apply_daily_upkeep()
        self._apply_enemy_passive_reactions()
        self._apply_storage_loss_events()
        self._progress_operation_if_applicable()

    def _tick_production_and_distribute_to_core(self) -> None:
        """Run production tick and distribute completed items to Core depot."""
        completed = self.production.tick()
        for output in completed:
            self._apply_production_output(output)

    def _apply_production_output(self, output: ProductionOutput) -> None:
        """Add completed production output to Core depot, then auto-dispatch if needed."""
        job_type = output.job_type
        quantity = output.quantity
        core_stock = self.logistics.depot_stocks[DepotNode.CORE]
        core_units = self.logistics.depot_units[DepotNode.CORE]
        supplies, units = self._build_production_payload(job_type, quantity)
        if job_type == ProductionJobType.AMMO:
            self.logistics.depot_stocks[DepotNode.CORE] = Supplies(
                ammo=core_stock.ammo + quantity,
                fuel=core_stock.fuel,
                med_spares=core_stock.med_spares,
            )
        elif job_type == ProductionJobType.FUEL:
            self.logistics.depot_stocks[DepotNode.CORE] = Supplies(
                ammo=core_stock.ammo,
                fuel=core_stock.fuel + quantity,
                med_spares=core_stock.med_spares,
            )
        elif job_type == ProductionJobType.MED_SPARES:
            self.logistics.depot_stocks[DepotNode.CORE] = Supplies(
                ammo=core_stock.ammo,
                fuel=core_stock.fuel,
                med_spares=core_stock.med_spares + quantity,
            )
        elif job_type == ProductionJobType.INFANTRY:
            self.logistics.depot_units[DepotNode.CORE] = UnitStock(
                infantry=core_units.infantry + quantity,
                walkers=core_units.walkers,
                support=core_units.support,
            )
        elif job_type == ProductionJobType.WALKERS:
            self.logistics.depot_units[DepotNode.CORE] = UnitStock(
                infantry=core_units.infantry,
                walkers=core_units.walkers + quantity,
                support=core_units.support,
            )
        elif job_type == ProductionJobType.SUPPORT:
            self.logistics.depot_units[DepotNode.CORE] = UnitStock(
                infantry=core_units.infantry,
                walkers=core_units.walkers,
                support=core_units.support + quantity,
            )

        if output.stop_at != DepotNode.CORE:
            self.logistics_service.create_shipment(
                self.logistics,
                DepotNode.CORE,
                output.stop_at,
                supplies,
                units,
                self.rng,
            )

    def _build_production_payload(
        self, job_type: ProductionJobType, quantity: int
    ) -> tuple[Supplies, UnitStock]:
        if job_type == ProductionJobType.AMMO:
            return Supplies(ammo=quantity, fuel=0, med_spares=0), UnitStock(0, 0, 0)
        if job_type == ProductionJobType.FUEL:
            return Supplies(ammo=0, fuel=quantity, med_spares=0), UnitStock(0, 0, 0)
        if job_type == ProductionJobType.MED_SPARES:
            return Supplies(ammo=0, fuel=0, med_spares=quantity), UnitStock(0, 0, 0)
        if job_type == ProductionJobType.INFANTRY:
            return Supplies(0, 0, 0), UnitStock(infantry=quantity, walkers=0, support=0)
        if job_type == ProductionJobType.WALKERS:
            return Supplies(0, 0, 0), UnitStock(infantry=0, walkers=quantity, support=0)
        return Supplies(0, 0, 0), UnitStock(infantry=0, walkers=0, support=quantity)

    def _tick_logistics(self) -> None:
        """Advance logistics state by one tick."""
        self.logistics_service.tick(self.logistics, self.rng)

    def _resupply_task_force_daily(self) -> None:
        """Resupply task force from key planet depot."""
        self.resupply_task_force()

    def _apply_daily_upkeep(self) -> None:
        """Apply daily fuel/med consumption and readiness degradation."""
        upkeep_fuel = 2
        upkeep_med = 1
        tf_supplies = self.task_force.supplies
        new_fuel = max(0, tf_supplies.fuel - upkeep_fuel)
        new_med = max(0, tf_supplies.med_spares - upkeep_med)
        self.task_force.supplies = Supplies(
            ammo=tf_supplies.ammo,
            fuel=new_fuel,
            med_spares=new_med,
        )
        if new_fuel == 0 or new_med == 0:
            self.task_force.readiness = max(0.0, self.task_force.readiness - 0.02)

    def _apply_enemy_passive_reactions(self) -> None:
        """Apply enemy fortification and strength growth."""
        if self.operation is None:
            self.planet.enemy.fortification = min(2.5, self.planet.enemy.fortification + 0.03)
            self.planet.enemy.strength_min = min(3.0, self.planet.enemy.strength_min + 0.02)
            self.planet.enemy.strength_max = min(4.0, self.planet.enemy.strength_max + 0.03)
        else:
            self.planet.enemy.fortification = min(2.0, self.planet.enemy.fortification + 0.01)

    def _apply_storage_loss_events(self) -> None:
        """Apply storage losses that increase with distance from Core."""
        for depot in DepotNode:
            risk = STORAGE_RISK_PER_DAY.get(depot, 0.0)
            if risk <= 0:
                continue
            stock = self.logistics.depot_stocks[depot]
            if stock.ammo == 0 and stock.fuel == 0 and stock.med_spares == 0:
                continue
            if self.rng.random() >= risk:
                continue
            min_loss, max_loss = STORAGE_LOSS_PCT_RANGE.get(depot, (0.0, 0.0))
            loss_pct = min_loss + (self.rng.random() * (max_loss - min_loss))
            self.logistics.depot_stocks[depot] = Supplies(
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

                if self.operation is not None and self.operation.decisions.is_complete():
                    self.acknowledge_phase_result()
                    if self.operation is not None:
                        self.operation.awaiting_player_decision = False

    def resupply_task_force(self) -> None:
        caps = Supplies(ammo=300, fuel=200, med_spares=100)
        depot_node = DepotNode.FRONT
        depot_stock = self.logistics.depot_stocks[depot_node]
        depot_units = self.logistics.depot_units[depot_node]
        tf_supplies = self.task_force.supplies

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
        self.task_force.supplies = Supplies(
            ammo=tf_supplies.ammo + ammo_transfer,
            fuel=tf_supplies.fuel + fuel_transfer,
            med_spares=tf_supplies.med_spares + med_transfer,
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

    def start_operation_phased(self, intent: OperationIntent) -> None:
        """Start a new phased operation. Player must submit decisions per phase."""
        if self.operation is not None:
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
        fort_mod = max(0, int((self.planet.enemy.fortification - 1.0) * 2))
        control_mod = max(0, int((1.0 - self.planet.control) * 2))
        estimated_days = base_days + fort_mod + control_mod
        estimated_days = max(duration_range[0], min(estimated_days, duration_range[1]))

        # Distribute days across phases
        phase_durations = self._calculate_phase_durations(intent.op_type, estimated_days)

        # Sample enemy strength once for determinism
        sampled_strength = self.rng.uniform(
            self.planet.enemy.strength_min,
            self.planet.enemy.strength_max,
        )

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
        self.task_force.supplies = Supplies(
            ammo=max(0, self.task_force.supplies.ammo - supplies_spent.ammo),
            fuel=max(0, self.task_force.supplies.fuel - supplies_spent.fuel),
            med_spares=max(0, self.task_force.supplies.med_spares - supplies_spent.med_spares),
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

        progress = approach_rules.get("progress_mod", 0.0) + prep_rules.get("progress_mod", 0.0)
        loss_mod = approach_rules.get("loss_mod", 0.0) + prep_rules.get("loss_mod", 0.0)

        log(f"approach_{d.approach_axis}", progress, "progress", f"Approach: {d.approach_axis}")
        log(f"fire_support_{d.fire_support_prep}", prep_rules.get("progress_mod", 0.0), "progress", f"Fire support: {d.fire_support_prep}")

        # Enemy factors affect phase 1
        strength_penalty = -0.10 * (op.sampled_enemy_strength - 1.0)
        control_penalty = -0.08 * (1.0 - self.planet.control)
        progress += strength_penalty + control_penalty

        log("enemy_strength", strength_penalty, "progress", f"Enemy strength {op.sampled_enemy_strength:.2f}")
        log("planet_control", control_penalty, "progress", f"Control level {self.planet.control:.2f}")

        # Supply costs for this phase
        base_ammo = 15 + (5 if d.fire_support_prep == "preparatory" else 0)
        base_fuel = 10 + (5 if d.approach_axis == "flank" else 0)
        ammo_cost = base_ammo * phase_days
        fuel_cost = base_fuel * phase_days

        # Check for shortages
        if self.task_force.supplies.ammo < ammo_cost:
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

        progress = posture_rules.get("progress_mod", 0.0) + risk_rules.get("progress_mod", 0.0)
        loss_mod = posture_rules.get("loss_mod", 0.0) + risk_rules.get("loss_mod", 0.0)
        variance_mult = risk_rules.get("variance_multiplier", 1.0)

        log(f"posture_{d.engagement_posture}", posture_rules.get("progress_mod", 0.0), "progress", f"Posture: {d.engagement_posture}")
        log(f"risk_{d.risk_tolerance}", risk_rules.get("progress_mod", 0.0), "progress", f"Risk tolerance: {d.risk_tolerance}")

        # Fortification is main factor in engagement
        fort = self.planet.enemy.fortification
        fort_penalty = -0.15 * (fort - 1.0)
        progress += fort_penalty
        log("enemy_fortification", fort_penalty, "progress", f"Fortification {fort:.2f} resists assault")

        # Variance from intel confidence
        support_role = self.rules.unit_roles.get("support")
        recon_reduction = 0.0
        if support_role and support_role.recon:
            recon_rating = self.task_force.composition.support * support_role.recon.get("variance_reduction", 0.30) / 10.0
            recon_reduction = min(0.5, recon_rating)
        base_variance = 0.20 * (1.0 - self.planet.enemy.confidence) * variance_mult
        variance = base_variance * (1.0 - recon_reduction)
        noise = self.rng.uniform(-variance, variance)
        progress += noise
        log("fog_of_war", noise, "progress", f"Combat variance (intel {int(self.planet.enemy.confidence * 100)}%)")
        if recon_reduction > 0.01:
            log("recon_variance_reduction", -base_variance * recon_reduction, "progress", f"Recon units reduce variance by {int(recon_reduction * 100)}%")

        # Supply costs
        ammo_cost = 25 * phase_days
        fuel_cost = 15 * phase_days
        med_cost = 5 * phase_days

        if self.task_force.supplies.fuel < fuel_cost:
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
                log("transport_protection", -protection_reduction, "losses", f"Walkers protect {max_protected} infantry")

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

        progress = exploit_rules.get("progress_mod", 0.0)
        loss_mod = exploit_rules.get("loss_mod", 0.0)

        log(f"exploit_{d.exploit_vs_secure}", progress, "progress", f"Exploit vs Secure: {d.exploit_vs_secure}")
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
        med_cost = 8 * phase_days
        supplies_spent = Supplies(ammo=5 * phase_days, fuel=5 * phase_days, med_spares=med_cost)

        if self.task_force.supplies.med_spares < med_cost:
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

        # Distribute losses (infantry takes more)
        infantry_losses = min(self.task_force.composition.infantry, int(losses * 0.6))
        walker_losses = min(self.task_force.composition.walkers, int(losses * 0.3))
        support_losses = min(self.task_force.composition.support, int(losses * 0.1))

        self.task_force.composition.infantry = max(0, self.task_force.composition.infantry - infantry_losses)
        self.task_force.composition.walkers = max(0, self.task_force.composition.walkers - walker_losses)
        self.task_force.composition.support = max(0, self.task_force.composition.support - support_losses)

        # Heavy losses reduce readiness
        if losses > total_units * 0.1:
            self.task_force.readiness = max(0.5, self.task_force.readiness - 0.1)

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
                self.planet.control = min(1.0, self.planet.control + 0.15)
                self.planet.enemy.fortification = max(0.6, self.planet.enemy.fortification - fort_reduction)
                self.planet.enemy.reinforcement_rate = max(0.0, self.planet.enemy.reinforcement_rate - reinf_reduction)
            elif end_state == "raid":
                self.planet.control = min(1.0, self.planet.control + 0.05)
                self.planet.enemy.reinforcement_rate = max(0.0, self.planet.enemy.reinforcement_rate - reinf_reduction)
            elif end_state == "destroy":
                self.planet.control = min(1.0, self.planet.control + 0.10)
                self.planet.enemy.fortification = max(0.6, self.planet.enemy.fortification - fort_reduction)
                self.planet.enemy.reinforcement_rate = max(0.0, self.planet.enemy.reinforcement_rate - reinf_reduction)
        elif end_state != "withdraw":
            self.planet.control = max(0.0, self.planet.control - 0.10)
            self.planet.enemy.fortification = min(2.5, self.planet.enemy.fortification + 0.10)

        top = self._top_factors(all_events)
        self.last_aar = AfterActionReport(
            outcome=outcome,
            target=op.target,
            operation_type=op.op_type.value,
            days=op.day_in_operation,
            losses=op.accumulated_losses,
            remaining_supplies=self.task_force.supplies,
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
        if self.task_force.supplies.ammo < ammo_cost:
            shortages += 1
            ammo_class = self.rules.supply_classes.get("ammo")
            if ammo_class:
                penalty = ammo_class.shortage_effects.get("progress_penalty", -0.30)
                supply_shortage_penalty += penalty
                log("ammo_shortage", "Phase 1", penalty, "progress", "Insufficient ammo reduces shaping effectiveness")
        if self.task_force.supplies.fuel < fuel_cost:
            shortages += 1
            fuel_class = self.rules.supply_classes.get("fuel")
            if fuel_class:
                penalty = fuel_class.shortage_effects.get("progress_penalty", -0.30)
                supply_shortage_penalty += penalty
                log("fuel_shortage", "Phase 2", penalty, "progress", "Insufficient fuel slows maneuver")
        if self.task_force.supplies.med_spares < med_cost:
            shortages += 1
            med_class = self.rules.supply_classes.get("med_spares")
            if med_class:
                penalty = med_class.shortage_effects.get("loss_multiplier", 1.20)
                loss_mod += (penalty - 1.0) * 0.1  # Convert multiplier to additive
                log("med_spares_shortage", "Phase 3", (penalty - 1.0) * 0.1, "losses", "Insufficient med/spares increases casualties")

        # Enemy factors
        base_progress = 1.0
        fort = self.planet.enemy.fortification
        fort_penalty = -0.25 * (fort - 1.0)
        log("enemy_fortification", "Phase 2", fort_penalty, "progress", f"Fortification {fort:.2f} resists assault")

        enemy_strength = self.rng.uniform(
            self.planet.enemy.strength_min,
            self.planet.enemy.strength_max,
        )
        strength_penalty = -0.20 * (enemy_strength - 1.0)
        log("enemy_strength", "Phase 1", strength_penalty, "progress", f"Enemy strength {enemy_strength:.2f}")

        # Planet control effect (lower control = harder)
        control_penalty = -0.15 * (1.0 - self.planet.control)
        log("planet_control", "Phase 1", control_penalty, "progress", f"Control level {self.planet.control:.2f} affects operations")

        # Signature Interaction 1: Recon reduces variance
        # Calculate recon rating from support units
        support_role = self.rules.unit_roles.get("support")
        recon_reduction = 0.0
        if support_role and support_role.recon:
            recon_rating = self.task_force.composition.support * support_role.recon.get("variance_reduction", 0.30) / 10.0
            recon_reduction = min(0.5, recon_rating)  # Cap at 50% reduction
        base_variance = 0.25 * (1.0 - self.planet.enemy.confidence) * variance_mult
        variance = base_variance * (1.0 - recon_reduction)
        noise = self.rng.uniform(-variance, variance)
        log("fog_of_war", "Phase 2", noise, "progress", f"Variance from intel ({int(self.planet.enemy.confidence * 100)}%) and recon")
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
        self.task_force.supplies = Supplies(
            ammo=max(0, self.task_force.supplies.ammo - ammo_cost),
            fuel=max(0, self.task_force.supplies.fuel - fuel_cost),
            med_spares=max(0, self.task_force.supplies.med_spares - med_cost),
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
            remaining_supplies=self.task_force.supplies,
            top_factors=top,
            phases=list(op.phase_history),
            events=events,
        )
        self.operation = None

    def _set_objective(self, target: OperationTarget, status: ObjectiveStatus) -> None:
        match target:
            case OperationTarget.FOUNDRY:
                self.planet.objectives.foundry = status
            case OperationTarget.COMMS:
                self.planet.objectives.comms = status
            case OperationTarget.POWER:
                self.planet.objectives.power = status

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
