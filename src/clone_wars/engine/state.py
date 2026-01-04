from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from random import Random

from clone_wars.engine.logging import Event, TopFactor
from clone_wars.engine.logistics import DepotNode, LogisticsState
from clone_wars.engine.ops import ActiveOperation, OperationPlan, OperationTarget
from clone_wars.engine.production import ProductionJobType, ProductionState
from clone_wars.engine.rules import Ruleset, RulesError
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
    days: int
    losses: int
    remaining_supplies: Supplies
    top_factors: list[TopFactor]
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

        # Production tick
        completed = self.production.tick()
        for job_type, quantity in completed:
            # Add completed production to Core depot
            core_stock = self.logistics.depot_stocks[DepotNode.CORE]
            core_units = self.logistics.depot_units[DepotNode.CORE]
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

        # Logistics tick
        self.logistics.tick(self.rng)

        # Resupply task force from key planet depot
        self.resupply_task_force()

        # Daily upkeep (passive attrition)
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

        # Enemy reactions
        if self.operation is None:
            self.planet.enemy.fortification = min(2.5, self.planet.enemy.fortification + 0.03)
            self.planet.enemy.strength_min = min(3.0, self.planet.enemy.strength_min + 0.02)
            self.planet.enemy.strength_max = min(4.0, self.planet.enemy.strength_max + 0.03)
        else:
            self.planet.enemy.fortification = min(2.0, self.planet.enemy.fortification + 0.01)

        if self.rng.random() < 0.05:
            stock = self.logistics.depot_stocks[DepotNode.KEY_PLANET]
            if stock.ammo > 0 or stock.fuel > 0 or stock.med_spares > 0:
                loss_pct = 0.10
                self.logistics.depot_stocks[DepotNode.KEY_PLANET] = Supplies(
                    ammo=max(0, int(stock.ammo * (1 - loss_pct))),
                    fuel=max(0, int(stock.fuel * (1 - loss_pct))),
                    med_spares=max(0, int(stock.med_spares * (1 - loss_pct))),
                )

        # Operation progress (if active)
        if self.operation is not None:
            self.operation.day_in_operation += 1
            if self.operation.day_in_operation >= self.operation.estimated_days:
                self.resolve_operation()

    def resupply_task_force(self) -> None:
        caps = Supplies(ammo=300, fuel=200, med_spares=100)
        depot_stock = self.logistics.depot_stocks[DepotNode.KEY_PLANET]
        tf_supplies = self.task_force.supplies

        ammo_deficit = max(0, caps.ammo - tf_supplies.ammo)
        fuel_deficit = max(0, caps.fuel - tf_supplies.fuel)
        med_deficit = max(0, caps.med_spares - tf_supplies.med_spares)

        ammo_transfer = min(depot_stock.ammo, ammo_deficit)
        fuel_transfer = min(depot_stock.fuel, fuel_deficit)
        med_transfer = min(depot_stock.med_spares, med_deficit)

        if ammo_transfer == 0 and fuel_transfer == 0 and med_transfer == 0:
            return

        self.logistics.depot_stocks[DepotNode.KEY_PLANET] = Supplies(
            ammo=depot_stock.ammo - ammo_transfer,
            fuel=depot_stock.fuel - fuel_transfer,
            med_spares=depot_stock.med_spares - med_transfer,
        )
        self.task_force.supplies = Supplies(
            ammo=tf_supplies.ammo + ammo_transfer,
            fuel=tf_supplies.fuel + fuel_transfer,
            med_spares=tf_supplies.med_spares + med_transfer,
        )

    def start_operation(self, plan: OperationPlan) -> None:
        if self.operation is not None:
            raise RuntimeError("Only one active operation allowed")

        # Determine operation duration based on target, enemy state, and plan
        # Use a simple rule: base duration from operation type (default to campaign)
        # Adjust for fortification and control
        base_days = 3  # Default campaign duration
        fort_mod = max(1, int(self.planet.enemy.fortification * 2))
        control_mod = max(0, int((1.0 - self.planet.control) * 2))
        estimated_days = base_days + fort_mod + control_mod

        # Clamp to reasonable range
        estimated_days = max(1, min(estimated_days, 10))

        self.operation = ActiveOperation(plan=plan, estimated_days=estimated_days)

    def resolve_operation(self) -> None:
        """Resolve active operation using rules-based engine with 3 signature interactions."""
        if self.operation is None:
            raise RuntimeError("No active operation")

        op = self.operation
        events: list[Event] = []

        def log(name: str, phase: str, value: float, delta: str, why: str) -> None:
            events.append(Event(name=name, phase=phase, value=value, delta=delta, why=why))

        plan = op.plan
        days = op.day_in_operation

        # Calculate supply costs (per day, multiplied by duration)
        base_ammo_per_day = 20
        base_fuel_per_day = 15
        base_med_per_day = 5
        ammo_cost = int((base_ammo_per_day + (5 if plan.fire_support_prep == "preparatory" else 0)) * days)
        fuel_cost = int((base_fuel_per_day + (5 if plan.approach_axis == "flank" else 0)) * days)
        med_cost = int(base_med_per_day * days)

        # Get rules
        approach_rules = self.rules.approach_axes.get(plan.approach_axis, {"progress_mod": 0.0, "loss_mod": 0.0})
        prep_rules = self.rules.fire_support_prep.get(plan.fire_support_prep, {"progress_mod": 0.0, "loss_mod": 0.0})
        posture_rules = self.rules.engagement_postures.get(plan.engagement_posture, {"progress_mod": 0.0, "loss_mod": 0.0})
        risk_rules = self.rules.risk_tolerances.get(plan.risk_tolerance, {"progress_mod": 0.0, "loss_mod": 0.0, "variance_multiplier": 1.0})
        exploit_rules = self.rules.exploit_vs_secure.get(plan.exploit_vs_secure, {"progress_mod": 0.0, "loss_mod": 0.0})
        end_state_rules = self.rules.end_states.get(plan.end_state, {"required_progress": 0.75, "fortification_reduction": 0.0, "reinforcement_reduction": 0.0})

        progress_mod = 0.0
        loss_mod = 0.0

        # Phase 1: Contact & Shaping
        app_progress = approach_rules.get("progress_mod", 0.0)
        app_loss = approach_rules.get("loss_mod", 0.0)
        progress_mod += app_progress
        loss_mod += app_loss
        log("approach_axis", "Phase 1", app_progress, "progress", f"Approach {plan.approach_axis}")
        log("approach_axis", "Phase 1", app_loss, "losses", f"Approach {plan.approach_axis}")

        prep_progress = prep_rules.get("progress_mod", 0.0)
        prep_loss = prep_rules.get("loss_mod", 0.0)
        progress_mod += prep_progress
        loss_mod += prep_loss
        log("fire_support_prep", "Phase 1", prep_progress, "progress", f"Fire support {plan.fire_support_prep}")
        log("fire_support_prep", "Phase 1", prep_loss, "losses", f"Fire support {plan.fire_support_prep}")

        # Phase 2: Main Engagement
        posture_progress = posture_rules.get("progress_mod", 0.0)
        posture_loss = posture_rules.get("loss_mod", 0.0)
        progress_mod += posture_progress
        loss_mod += posture_loss
        log("engagement_posture", "Phase 2", posture_progress, "progress", f"Posture {plan.engagement_posture}")
        log("engagement_posture", "Phase 2", posture_loss, "losses", f"Posture {plan.engagement_posture}")

        risk_progress = risk_rules.get("progress_mod", 0.0)
        risk_loss = risk_rules.get("loss_mod", 0.0)
        variance_mult = risk_rules.get("variance_multiplier", 1.0)
        progress_mod += risk_progress
        loss_mod += risk_loss
        log("risk_tolerance", "Phase 2", risk_progress, "progress", f"Risk {plan.risk_tolerance}")
        log("risk_tolerance", "Phase 2", risk_loss, "losses", f"Risk {plan.risk_tolerance}")

        # Phase 3: Exploit & Consolidate
        exploit_progress = exploit_rules.get("progress_mod", 0.0)
        exploit_loss = exploit_rules.get("loss_mod", 0.0)
        progress_mod += exploit_progress
        loss_mod += exploit_loss
        log("exploit_vs_secure", "Phase 3", exploit_progress, "progress", f"Exploit {plan.exploit_vs_secure}")
        log("exploit_vs_secure", "Phase 3", exploit_loss, "losses", f"Exploit {plan.exploit_vs_secure}")

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
        if plan.end_state == "withdraw":
            outcome = outcome_map["withdraw"]
            success = False
        else:
            outcome = outcome_map[plan.end_state] if success else "FAILED"

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
            if plan.end_state == "capture":
                self._set_objective(op.target, ObjectiveStatus.SECURED)
                self.planet.control = min(1.0, self.planet.control + 0.15)  # Increase control
                self.planet.enemy.fortification = max(0.6, self.planet.enemy.fortification - fort_reduction)
                self.planet.enemy.reinforcement_rate = max(0.0, self.planet.enemy.reinforcement_rate - reinf_reduction)
                log("objective_secured", "Phase 3", +1.0, "objective", "Objective secured; enemy effects reduced, control increased")
            elif plan.end_state == "raid":
                self.planet.control = min(1.0, self.planet.control + 0.05)
                self.planet.enemy.reinforcement_rate = max(0.0, self.planet.enemy.reinforcement_rate - reinf_reduction)
                log("objective_raided", "Phase 3", +0.6, "objective", "Raid disrupts reinforcement flow")
            elif plan.end_state == "destroy":
                self.planet.control = min(1.0, self.planet.control + 0.10)
                self.planet.enemy.fortification = max(0.6, self.planet.enemy.fortification - fort_reduction)
                self.planet.enemy.reinforcement_rate = max(0.0, self.planet.enemy.reinforcement_rate - reinf_reduction)
                log("objective_destroyed", "Phase 3", +0.8, "objective", "Destruction weakens defenses")
        elif plan.end_state != "withdraw":
            # Failure consequences: lose control, increase fortification
            self.planet.control = max(0.0, self.planet.control - 0.10)
            self.planet.enemy.fortification = min(2.5, self.planet.enemy.fortification + 0.10)
            log("operation_failed", "Phase 3", -1.0, "objective", "Failure increases enemy fortification and reduces control")

        top = self._top_factors(events)
        self.last_aar = AfterActionReport(
            outcome=outcome,
            target=op.target,
            days=days,
            losses=losses,
            remaining_supplies=self.task_force.supplies,
            top_factors=top,
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
