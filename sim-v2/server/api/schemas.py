from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, validate_by_name=True)


class Position(CamelModel):
    x: float
    y: float


class Supplies(CamelModel):
    ammo: int = Field(..., ge=0)
    fuel: int = Field(..., ge=0)
    med_spares: int = Field(..., alias="medSpares", ge=0)


class UnitStock(CamelModel):
    infantry: int = Field(..., ge=0)
    walkers: int = Field(..., ge=0)
    support: int = Field(..., ge=0)


class IntelRange(CamelModel):
    min: int
    max: int


class EnemyIntel(CamelModel):
    infantry: IntelRange
    walkers: IntelRange
    support: IntelRange
    fortification: float
    reinforcement_rate: float = Field(..., alias="reinforcementRate")
    cohesion: float
    intel_confidence: float = Field(..., alias="intelConfidence")


class PlanetObjective(CamelModel):
    id: str
    label: str
    status: str


class ContestedPlanet(CamelModel):
    control: float
    objectives: List[PlanetObjective]
    enemy: EnemyIntel


class SystemNode(CamelModel):
    id: str
    label: str
    kind: str
    description: str
    position: Position


class Route(CamelModel):
    origin: str
    destination: str
    travel_days: int = Field(..., alias="travelDays")
    interdiction_risk: float = Field(..., alias="interdictionRisk")


class MapLeg(CamelModel):
    origin: str
    destination: str
    travel_days: int = Field(..., alias="travelDays")
    interdiction_risk: float = Field(..., alias="interdictionRisk")


class MapNode(CamelModel):
    id: str
    label: str
    x: float
    y: float
    type: str
    size: str
    is_labeled: bool = Field(..., alias="isLabeled")
    subtitle1: str
    subtitle2: Optional[str] = None
    severity: str


class MapConnection(CamelModel):
    id: str
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    status: str
    risk: float
    aggregated_travel_days: int = Field(..., alias="aggregatedTravelDays")
    underlying_legs: Optional[List[MapLeg]] = Field(None, alias="underlyingLegs")


class MapView(CamelModel):
    nodes: List[MapNode]
    connections: List[MapConnection]


class Depot(CamelModel):
    id: str
    label: str
    supplies: Supplies
    units: UnitStock


class Shipment(CamelModel):
    id: int
    origin: str
    destination: str
    days_remaining: int = Field(..., alias="daysRemaining")
    total_days: int = Field(..., alias="totalDays")
    interdicted: bool
    interdiction_loss_pct: float = Field(..., alias="interdictionLossPct")
    supplies: Supplies
    units: UnitStock


class CargoShip(CamelModel):
    id: str
    name: str
    location: str
    state: str
    destination: Optional[str]
    days_remaining: int = Field(..., alias="daysRemaining")
    total_days: int = Field(..., alias="totalDays")
    supplies: Supplies
    units: UnitStock


class TransitLogEntry(CamelModel):
    day: int
    message: str
    event_type: str = Field(..., alias="eventType")


class TransportOrder(CamelModel):
    order_id: str = Field(..., alias="orderId")
    origin: str
    final_destination: str = Field(..., alias="finalDestination")
    current_location: str = Field(..., alias="currentLocation")
    status: str
    supplies: Supplies
    units: UnitStock
    in_transit_leg: Optional[Tuple[str, str]] = Field(None, alias="inTransitLeg")
    carrier_id: Optional[str] = Field(None, alias="carrierId")
    blocked_reason: Optional[str] = Field(None, alias="blockedReason")


class LogisticsState(CamelModel):
    depots: List[Depot]
    routes: List[Route]
    shipments: List[Shipment]
    ships: List[CargoShip]
    active_orders: List[TransportOrder] = Field(..., alias="activeOrders")
    transit_log: List[TransitLogEntry] = Field(..., alias="transitLog")


class ProductionJob(CamelModel):
    type: str
    quantity: int
    remaining: int
    stop_at: str = Field(..., alias="stopAt")
    eta_days: int = Field(..., alias="etaDays")


class ProductionState(CamelModel):
    factories: int
    max_factories: int = Field(..., alias="maxFactories")
    slots_per_factory: int = Field(..., alias="slotsPerFactory")
    capacity: int
    costs: Dict[str, int]
    jobs: List[ProductionJob]


class BarracksState(CamelModel):
    barracks: int
    max_barracks: int = Field(..., alias="maxBarracks")
    slots_per_barracks: int = Field(..., alias="slotsPerBarracks")
    capacity: int
    costs: Dict[str, int]
    jobs: List[ProductionJob]


class DecisionPhase1(CamelModel):
    approach_axis: str = Field(..., alias="approachAxis")
    fire_support_prep: str = Field(..., alias="fireSupportPrep")


class DecisionPhase2(CamelModel):
    engagement_posture: str = Field(..., alias="engagementPosture")
    risk_tolerance: str = Field(..., alias="riskTolerance")


class DecisionPhase3(CamelModel):
    exploit_vs_secure: str = Field(..., alias="exploitVsSecure")
    end_state: str = Field(..., alias="endState")


class OperationDecisionSummary(CamelModel):
    phase1: Optional[DecisionPhase1] = None
    phase2: Optional[DecisionPhase2] = None
    phase3: Optional[DecisionPhase3] = None


class PhaseSummary(CamelModel):
    progress_delta: float = Field(..., alias="progressDelta")
    losses: int
    enemy_losses: int = Field(..., alias="enemyLosses")
    supplies_spent: Supplies = Field(..., alias="suppliesSpent")
    readiness_delta: float = Field(..., alias="readinessDelta")
    cohesion_delta: float = Field(..., alias="cohesionDelta")
    enemy_cohesion_delta: float = Field(..., alias="enemyCohesionDelta")


class Event(CamelModel):
    name: str
    value: float
    delta: str
    why: str
    phase: str


class BattleSupplySnapshot(CamelModel):
    ammo_before: int = Field(..., alias="ammoBefore")
    fuel_before: int = Field(..., alias="fuelBefore")
    med_before: int = Field(..., alias="medBefore")
    ammo_spent: int = Field(..., alias="ammoSpent")
    fuel_spent: int = Field(..., alias="fuelSpent")
    med_spent: int = Field(..., alias="medSpent")
    ammo_ratio: float = Field(..., alias="ammoRatio")
    fuel_ratio: float = Field(..., alias="fuelRatio")
    med_ratio: float = Field(..., alias="medRatio")
    shortage_flags: List[str] = Field(..., alias="shortageFlags")


class BattleDayTick(CamelModel):
    day_index: int = Field(..., alias="dayIndex")
    global_day: int = Field(..., alias="globalDay")
    phase: str
    terrain_id: str = Field(..., alias="terrainId")
    infrastructure: int
    combat_width_multiplier: float = Field(..., alias="combatWidthMultiplier")
    force_limit_battalions: int = Field(..., alias="forceLimitBattalions")
    engagement_cap_manpower: int = Field(..., alias="engagementCapManpower")
    attacker_eligible_manpower: int = Field(..., alias="attackerEligibleManpower")
    defender_eligible_manpower: int = Field(..., alias="defenderEligibleManpower")
    attacker_engaged_manpower: int = Field(..., alias="attackerEngagedManpower")
    defender_engaged_manpower: int = Field(..., alias="defenderEngagedManpower")
    attacker_engagement_ratio: float = Field(..., alias="attackerEngagementRatio")
    defender_engagement_ratio: float = Field(..., alias="defenderEngagementRatio")
    attacker_advantage_expansion: float = Field(..., alias="attackerAdvantageExpansion")
    defender_advantage_expansion: float = Field(..., alias="defenderAdvantageExpansion")
    your_power: float = Field(..., alias="yourPower")
    enemy_power: float = Field(..., alias="enemyPower")
    your_advantage: float = Field(..., alias="yourAdvantage")
    initiative: bool
    progress_delta: float = Field(..., alias="progressDelta")
    your_losses: Dict[str, int] = Field(..., alias="yourLosses")
    enemy_losses: Dict[str, int] = Field(..., alias="enemyLosses")
    your_remaining: Dict[str, int] = Field(..., alias="yourRemaining")
    enemy_remaining: Dict[str, int] = Field(..., alias="enemyRemaining")
    your_cohesion: float = Field(..., alias="yourCohesion")
    enemy_cohesion: float = Field(..., alias="enemyCohesion")
    supplies: BattleSupplySnapshot
    tags: List[str]


class PhaseRecord(CamelModel):
    phase: str
    start_day: int = Field(..., alias="startDay")
    end_day: int = Field(..., alias="endDay")
    decisions: Optional[Dict[str, str]]
    summary: PhaseSummary
    days: List[BattleDayTick]
    events: List[Event]


class OperationState(CamelModel):
    target: str
    op_type: str = Field(..., alias="opType")
    current_phase: str = Field(..., alias="currentPhase")
    estimated_total_days: int = Field(..., alias="estimatedTotalDays")
    phase_durations: Dict[str, int] = Field(..., alias="phaseDurations")
    day_in_operation: int = Field(..., alias="dayInOperation")
    day_in_phase: int = Field(..., alias="dayInPhase")
    awaiting_decision: bool = Field(..., alias="awaitingDecision")
    pending_phase_record: Optional[PhaseRecord] = Field(None, alias="pendingPhaseRecord")
    decisions: OperationDecisionSummary
    phase_history: List[PhaseRecord] = Field(..., alias="phaseHistory")
    sampled_enemy_strength: Optional[float] = Field(None, alias="sampledEnemyStrength")
    latest_battle_day: Optional[BattleDayTick] = Field(None, alias="latestBattleDay")
    current_phase_days: List[BattleDayTick] = Field(..., alias="currentPhaseDays")


class TopFactor(CamelModel):
    name: str
    value: float
    delta: str
    why: str


class AfterActionReport(CamelModel):
    kind: str
    outcome: str
    target: str
    operation_type: str = Field(..., alias="operationType")
    days: int
    losses: int
    enemy_losses: int = Field(..., alias="enemyLosses")
    remaining_supplies: Supplies = Field(..., alias="remainingSupplies")
    top_factors: List[TopFactor] = Field(..., alias="topFactors")
    phases: List[PhaseRecord]
    events: List[Event]


class TaskForce(CamelModel):
    composition: UnitStock
    readiness: float
    cohesion: float
    location: str
    supplies: Supplies


class CampaignNextAction(CamelModel):
    id: str
    label: str
    reason: str
    blocking_reason: Optional[str] = Field(None, alias="blockingReason")


class CampaignReadiness(CamelModel):
    force_score: float = Field(..., alias="forceScore")
    supply_score: float = Field(..., alias="supplyScore")
    route_score: float = Field(..., alias="routeScore")
    intel_score: float = Field(..., alias="intelScore")
    overall_score: float = Field(..., alias="overallScore")


class CampaignSupplyForecast(CamelModel):
    ammo_days: float = Field(..., alias="ammoDays")
    fuel_days: float = Field(..., alias="fuelDays")
    med_days: float = Field(..., alias="medDays")
    bottleneck: str


class CampaignObjectiveStatus(CamelModel):
    id: str
    label: str
    status: str


class CampaignObjectiveProgress(CamelModel):
    secured: int
    total: int
    objectives: List[CampaignObjectiveStatus]


class CampaignOperationSnapshot(CamelModel):
    eta_days: int = Field(..., alias="etaDays")
    current_phase: str = Field(..., alias="currentPhase")
    day_in_phase: int = Field(..., alias="dayInPhase")
    day_in_operation: int = Field(..., alias="dayInOperation")
    required_progress_hint: float = Field(..., alias="requiredProgressHint")


class CampaignLogEntry(CamelModel):
    day: int
    kind: str
    message: str


class CampaignView(CamelModel):
    stage: str
    next_action: CampaignNextAction = Field(..., alias="nextAction")
    blockers: List[str]
    readiness: CampaignReadiness
    supply_forecast: CampaignSupplyForecast = Field(..., alias="supplyForecast")
    objective_progress: CampaignObjectiveProgress = Field(..., alias="objectiveProgress")
    operation_snapshot: Optional[CampaignOperationSnapshot] = Field(None, alias="operationSnapshot")
    campaign_log: List[CampaignLogEntry] = Field(..., alias="campaignLog")


class GameStateResponse(CamelModel):
    day: int
    action_points: int = Field(..., alias="actionPoints")
    faction_turn: str = Field(..., alias="factionTurn")
    system_nodes: List[SystemNode] = Field(..., alias="systemNodes")
    contested_planet: ContestedPlanet = Field(..., alias="contestedPlanet")
    task_force: TaskForce = Field(..., alias="taskForce")
    production: ProductionState
    barracks: BarracksState
    logistics: LogisticsState
    operation: Optional[OperationState]
    last_aar: Optional[AfterActionReport] = Field(None, alias="lastAar")
    map_view: Optional[MapView] = Field(None, alias="mapView")
    campaign_view: CampaignView = Field(..., alias="campaignView")


class ApiResponse(CamelModel):
    ok: bool
    message: Optional[str] = None
    message_kind: Optional[str] = Field(None, alias="messageKind")
    state: Optional[GameStateResponse] = None


class DispatchRequest(CamelModel):
    origin: str
    destination: str
    supplies: Supplies
    units: UnitStock


class ProductionRequest(CamelModel):
    job_type: str = Field(..., alias="jobType")
    quantity: int = Field(..., ge=1)


class OperationStartRequest(CamelModel):
    target: str
    op_type: str = Field(..., alias="opType")


class PhaseDecisionRequest(CamelModel):
    axis: Optional[str] = None
    fire: Optional[str] = None
    posture: Optional[str] = None
    risk: Optional[str] = None
    focus: Optional[str] = None
    end_state: Optional[str] = Field(None, alias="endState")


class CatalogOption(CamelModel):
    id: str
    label: str
    description: Optional[str] = None


class CatalogImpact(CamelModel):
    progress: Optional[float] = None
    losses: Optional[float] = None
    variance: Optional[float] = None
    supplies: Optional[float] = None
    fortification: Optional[float] = None


class CatalogAvailability(CamelModel):
    enabled: bool
    reason: Optional[str] = None


class CatalogOptionWithMeta(CatalogOption):
    impact: Optional[CatalogImpact] = None
    availability: Optional[CatalogAvailability] = None


class CatalogPhase1(CamelModel):
    approach_axis: List[CatalogOptionWithMeta] = Field(..., alias="approachAxis")
    fire_support_prep: List[CatalogOptionWithMeta] = Field(..., alias="fireSupportPrep")


class CatalogPhase2(CamelModel):
    engagement_posture: List[CatalogOptionWithMeta] = Field(..., alias="engagementPosture")
    risk_tolerance: List[CatalogOptionWithMeta] = Field(..., alias="riskTolerance")


class CatalogPhase3(CamelModel):
    exploit_vs_secure: List[CatalogOptionWithMeta] = Field(..., alias="exploitVsSecure")
    end_state: List[CatalogOptionWithMeta] = Field(..., alias="endState")


class CatalogDecisions(CamelModel):
    phase1: CatalogPhase1
    phase2: CatalogPhase2
    phase3: CatalogPhase3


class CatalogResponse(CamelModel):
    operation_targets: List[CatalogOption] = Field(..., alias="operationTargets")
    operation_types: List[CatalogOptionWithMeta] = Field(..., alias="operationTypes")
    decisions: CatalogDecisions
    objectives: List[CatalogOption]
