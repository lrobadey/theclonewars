export type Supplies = {
  ammo: number;
  fuel: number;
  medSpares: number;
};

export type UnitStock = {
  infantry: number;
  walkers: number;
  support: number;
};

export type ObjectiveStatus = "enemy" | "contested" | "secured";

export type PlanetObjective = {
  id: "foundry" | "comms" | "power";
  label: string;
  status: ObjectiveStatus;
};

export type EnemyIntel = {
  infantry: { min: number; max: number; actual: number };
  walkers: { min: number; max: number; actual: number };
  support: { min: number; max: number; actual: number };
  fortification: number;
  reinforcementRate: number;
  cohesion: number;
  intelConfidence: number;
};

export type ContestedPlanet = {
  control: number;
  objectives: PlanetObjective[];
  enemy: EnemyIntel;
};

export type SystemNode = {
  id: string;
  label: string;
  kind: "core" | "deep" | "tactical";
  description: string;
  position: { x: number; y: number };
};

export type Route = {
  origin: string;
  destination: string;
  travelDays: number;
  interdictionRisk: number;
};

export type MapLeg = {
  origin: string;
  destination: string;
  travelDays: number;
  interdictionRisk: number;
};

export type MapNode = {
  id: string;
  label: string;
  x: number;
  y: number;
  type: "core" | "deep" | "contested";
  size: "large" | "medium" | "small";
  isLabeled: boolean;
  subtitle1: string;
  subtitle2?: string;
  severity: "good" | "warn" | "danger";
};

export type MapConnection = {
  id: string;
  from: string;
  to: string;
  status: "active" | "disrupted" | "blocked";
  risk: number;
  aggregatedTravelDays: number;
  underlyingLegs?: MapLeg[];
};

export type MapView = {
  nodes: MapNode[];
  connections: MapConnection[];
};

export type Depot = {
  id: string;
  label: string;
  supplies: Supplies;
  units: UnitStock;
};

export type Shipment = {
  id: number;
  origin: string;
  destination: string;
  daysRemaining: number;
  totalDays: number;
  interdicted: boolean;
  interdictionLossPct: number;
  supplies: Supplies;
  units: UnitStock;
};

export type CargoShip = {
  id: string;
  name: string;
  location: string;
  state: string;
  destination: string | null;
  daysRemaining: number;
  totalDays: number;
  supplies: Supplies;
  units: UnitStock;
};

export type TransitLogEntry = {
  day: number;
  message: string;
  eventType: string;
};

export type TransportOrder = {
  orderId: string;
  origin: string;
  finalDestination: string;
  currentLocation: string;
  status: string;
  supplies: Supplies;
  units: UnitStock;
  inTransitLeg: [string, string] | null;
  carrierId: string | null;
  blockedReason?: string | null;
};

export type LogisticsState = {
  depots: Depot[];
  routes: Route[];
  shipments: Shipment[];
  ships: CargoShip[];
  activeOrders: TransportOrder[];
  transitLog: TransitLogEntry[];
};

export type ProductionJob = {
  type: string;
  quantity: number;
  remaining: number;
  stopAt: string;
  etaDays: number;
};

export type ProductionState = {
  factories: number;
  maxFactories: number;
  slotsPerFactory: number;
  capacity: number;
  costs: Record<string, number>;
  jobs: ProductionJob[];
};

export type BarracksState = {
  barracks: number;
  maxBarracks: number;
  slotsPerBarracks: number;
  capacity: number;
  costs: Record<string, number>;
  jobs: ProductionJob[];
};

export type OperationDecisionSummary = {
  phase1?: { approachAxis: string; fireSupportPrep: string };
  phase2?: { engagementPosture: string; riskTolerance: string };
  phase3?: { exploitVsSecure: string; endState: string };
};

export type PhaseSummary = {
  progressDelta: number;
  losses: number;
  enemyLosses: number;
  suppliesSpent: Supplies;
  readinessDelta: number;
  cohesionDelta: number;
  enemyCohesionDelta: number;
};

export type BattleSupplySnapshot = {
  ammoBefore: number;
  fuelBefore: number;
  medBefore: number;
  ammoSpent: number;
  fuelSpent: number;
  medSpent: number;
  ammoRatio: number;
  fuelRatio: number;
  medRatio: number;
  shortageFlags: string[];
};

export type BattleDayTick = {
  dayIndex: number;
  globalDay: number;
  phase: string;
  terrainId: string;
  infrastructure: number;
  combatWidthMultiplier: number;
  forceLimitBattalions: number;
  engagementCapManpower: number;
  attackerEligibleManpower: number;
  defenderEligibleManpower: number;
  attackerEngagedManpower: number;
  defenderEngagedManpower: number;
  attackerEngagementRatio: number;
  defenderEngagementRatio: number;
  attackerAdvantageExpansion: number;
  defenderAdvantageExpansion: number;
  yourPower: number;
  enemyPower: number;
  yourAdvantage: number;
  initiative: boolean;
  progressDelta: number;
  yourLosses: Record<string, number>;
  enemyLosses: Record<string, number>;
  yourRemaining: Record<string, number>;
  enemyRemaining: Record<string, number>;
  yourCohesion: number;
  enemyCohesion: number;
  supplies: BattleSupplySnapshot;
  tags: string[];
};

export type PhaseRecord = {
  phase: string;
  startDay: number;
  endDay: number;
  decisions: Record<string, string> | null;
  summary: PhaseSummary;
  days: BattleDayTick[];
  events: { name: string; value: number; delta: string; why: string; phase: string }[];
};

export type OperationState = {
  target: string;
  opType: string;
  currentPhase: string;
  estimatedTotalDays: number;
  phaseDurations: Record<string, number>;
  dayInOperation: number;
  dayInPhase: number;
  awaitingDecision: boolean;
  pendingPhaseRecord: PhaseRecord | null;
  decisions: OperationDecisionSummary;
  phaseHistory: PhaseRecord[];
  sampledEnemyStrength: number | null;
  latestBattleDay: BattleDayTick | null;
  currentPhaseDays: BattleDayTick[];
};

export type TopFactor = {
  name: string;
  value: number;
  delta: string;
  why: string;
};

export type AfterActionReport = {
  kind: "operation";
  outcome: string;
  target: string;
  operationType: string;
  days: number;
  losses: number;
  enemyLosses: number;
  remainingSupplies: Supplies;
  topFactors: TopFactor[];
  phases: PhaseRecord[];
  events: { name: string; value: number; delta: string; why: string; phase: string }[];
};

export type GameStateResponse = {
  day: number;
  actionPoints: number;
  factionTurn: string;
  systemNodes: SystemNode[];
  contestedPlanet: ContestedPlanet;
  taskForce: {
    composition: UnitStock;
    readiness: number;
    cohesion: number;
    location: string;
    supplies: Supplies;
  };
  production: ProductionState;
  barracks: BarracksState;
  logistics: LogisticsState;
  operation: OperationState | null;
  lastAar: AfterActionReport | null;
  mapView?: MapView;
};

export type ApiResponse = {
  ok: boolean;
  message?: string;
  messageKind?: "info" | "error" | "accent";
  state?: GameStateResponse;
};

export type PhaseDecisionRequest = {
  axis?: string;
  fire?: string;
  posture?: string;
  risk?: string;
  focus?: string;
  endState?: string;
};

export type CatalogOption = {
  id: string;
  label: string;
  description?: string;
};

export type CatalogResponse = {
  operationTargets: CatalogOption[];
  operationTypes: CatalogOption[];
  decisions: {
    phase1: {
      approachAxis: CatalogOption[];
      fireSupportPrep: CatalogOption[];
    };
    phase2: {
      engagementPosture: CatalogOption[];
      riskTolerance: CatalogOption[];
    };
    phase3: {
      exploitVsSecure: CatalogOption[];
      endState: CatalogOption[];
    };
  };
  objectives: CatalogOption[];
};
