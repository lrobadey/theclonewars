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
  suppliesSpent: Supplies;
  readinessDelta: number;
  cohesionDelta: number;
};

export type PhaseRecord = {
  phase: string;
  startDay: number;
  endDay: number;
  decisions: Record<string, string> | null;
  summary: PhaseSummary;
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
};

export type RaidState = {
  tick: number;
  maxTicks: number;
  yourCohesion: number;
  enemyCohesion: number;
  yourCasualties: number;
  enemyCasualties: number;
  outcome: string | null;
  reason: string | null;
  tickLog: { tick: number; event: string; beat: string }[];
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
  remainingSupplies: Supplies;
  topFactors: TopFactor[];
  phases: PhaseRecord[];
  events: { name: string; value: number; delta: string; why: string; phase: string }[];
};

export type RaidReport = {
  kind: "raid";
  outcome: string;
  reason: string;
  target: string;
  ticks: number;
  yourCasualties: number;
  enemyCasualties: number;
  yourRemaining: Record<string, number>;
  enemyRemaining: Record<string, number>;
  suppliesUsed: Supplies;
  keyMoments: string[];
  topFactors: { name: string; value: number; why: string }[];
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
  raid: RaidState | null;
  lastAar: AfterActionReport | RaidReport | null;
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
