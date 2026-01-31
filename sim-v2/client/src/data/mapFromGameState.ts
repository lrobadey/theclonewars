import type { GameStateResponse, SystemNode, Route } from '../api/types';

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
}

const SCALE_X = 1200 / 100;
const SCALE_Y = 400 / 100;

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

  // Filter connections to only those between the 3 main nodes
  const mainNodeIds = new Set(['new_system_core', 'deep_space', 'contested_front']);
  const connections: ConnectionData[] = state.logistics.routes
    .filter((route: Route) => mainNodeIds.has(route.origin) && mainNodeIds.has(route.destination))
    .map((route: Route) => {
    let status: 'active' | 'disrupted' | 'blocked' = 'active';
    if (route.interdictionRisk > 0.6) {
      status = 'blocked';
    } else if (route.interdictionRisk > 0.3) {
      status = 'disrupted';
    }

    return {
      id: `${route.origin}-${route.destination}`,
      from: route.origin,
      to: route.destination,
      status,
      risk: route.interdictionRisk,
    };
  });

  return { nodes, connections };
}
