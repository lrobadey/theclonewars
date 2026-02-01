import type { GameStateResponse, SystemNode } from '../api/types';

export interface MapNodeData {
  id: string;
  label: string;
  x: number;
  y: number;
  type: 'core' | 'deep' | 'contested';
  size: 'large' | 'medium' | 'small';
  isLabeled: boolean;
}

export interface ConnectionData {
  id: string;
  from: string;
  to: string;
  status: 'active' | 'disrupted' | 'blocked';
  risk: number;
  aggregatedTravelDays?: number;
  underlyingLegs?: Array<{
    origin: string;
    destination: string;
    travelDays: number;
    interdictionRisk: number;
  }>;
}

const SCALE_X = 1200 / 100;
const SCALE_Y = 400 / 100;

const STRATEGIC_NODE_IDS = new Set(['new_system_core', 'deep_space', 'contested_front']);

function toStrategicNodeId(systemNodeId: string): string | null {
  if (systemNodeId === 'new_system_core') return 'new_system_core';
  if (systemNodeId === 'deep_space') return 'deep_space';
  if (systemNodeId.startsWith('contested_')) return 'contested_front';
  return null;
}

function statusFromRisk(risk: number): 'active' | 'disrupted' | 'blocked' {
  if (risk > 0.6) return 'blocked';
  if (risk > 0.3) return 'disrupted';
  return 'active';
}

export function mapFromGameState(state: GameStateResponse) {
  // Filter to only show the 3 main labeled nodes
  const nodes: MapNodeData[] = state.systemNodes
    .filter((node: SystemNode) => {
      // Only include the 3 main systems
      return node.id === 'new_system_core' || 
             node.id === 'deep_space' || 
             node.id === 'contested_front';
    })
    .map((node: SystemNode) => {
      let uiLabel = '';
      let uiType: 'core' | 'deep' | 'contested' = 'deep';
      let uiSize: 'large' | 'medium' | 'small' = 'small';
      let isLabeled = false;

      // Map logic from requirements:
      // new_system_core -> CORE WORLDS, core, large, Yes
      // deep_space -> DEEP SPACE, deep, medium, Yes
      // contested_front -> CONTESTED SYSTEM, contested, medium, Yes

      if (node.id === 'new_system_core') {
        uiLabel = 'CORE WORLDS';
        uiType = 'core';
        uiSize = 'large';
        isLabeled = true;
      } else if (node.id === 'deep_space') {
        uiLabel = 'DEEP SPACE';
        uiType = 'deep';
        uiSize = 'medium';
        isLabeled = true;
      } else if (node.id === 'contested_front') {
        uiLabel = 'CONTESTED SYSTEM';
        uiType = 'contested';
        uiSize = 'medium';
        isLabeled = true;
      }

      return {
        id: node.id,
        label: uiLabel,
        x: node.position.x * SCALE_X,
        y: node.position.y * SCALE_Y,
        type: uiType,
        size: uiSize,
        isLabeled,
      };
    });

  // Build strategic connections by aggregating backend routes into 3 UI nodes
  const aggregated = new Map<
    string,
    {
      from: string;
      to: string;
      maxRisk: number;
      totalTravelDays: number;
      legs: Array<{
        origin: string;
        destination: string;
        travelDays: number;
        interdictionRisk: number;
      }>;
    }
  >();

  for (const route of state.logistics.routes) {
    const originUi = toStrategicNodeId(route.origin);
    const destUi = toStrategicNodeId(route.destination);
    if (!originUi || !destUi) continue;
    if (!STRATEGIC_NODE_IDS.has(originUi) || !STRATEGIC_NODE_IDS.has(destUi)) continue;
    if (originUi === destUi) continue;

    const key = `${originUi}-${destUi}`;
    const existing = aggregated.get(key);
    const maxRisk = Math.max(existing?.maxRisk ?? 0, route.interdictionRisk);
    const totalTravelDays = (existing?.totalTravelDays ?? 0) + route.travelDays;
    const legs = existing?.legs ?? [];

    aggregated.set(key, {
      from: originUi,
      to: destUi,
      maxRisk,
      totalTravelDays,
      legs: [
        ...legs,
        {
          origin: route.origin,
          destination: route.destination,
          travelDays: route.travelDays,
          interdictionRisk: route.interdictionRisk,
        },
      ],
    });
  }

  const connections: ConnectionData[] = Array.from(aggregated.entries()).map(([key, value]) => ({
    id: key,
    from: value.from,
    to: value.to,
    status: statusFromRisk(value.maxRisk),
    risk: value.maxRisk,
    aggregatedTravelDays: value.totalTravelDays,
    underlyingLegs: value.legs,
  }));

  return { nodes, connections };
}
