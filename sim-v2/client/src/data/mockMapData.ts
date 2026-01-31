export type NodeType = 'core' | 'deep' | 'contested';
export type NodeStatus = 'stable' | 'warning' | 'critical';
export type NodeSize = 'small' | 'medium' | 'large';
export type ConnectionStatus = 'active' | 'disrupted' | 'blocked';
export type GlobalStatus = 'stable' | 'alert' | 'critical';

export interface MapNodeData {
  id: string;
  type: NodeType;
  label: string;
  position: { x: number; y: number };
  status?: NodeStatus;
  size?: NodeSize;
}

export interface ConnectionData {
  id: string;
  from: string;
  to: string;
  status: ConnectionStatus;
  flowDirection?: 'forward' | 'reverse' | 'bidirectional';
}

export interface HeaderData {
  simulationName: string;
  factions: [string, string];
  day: number;
  actionPoints: number;
  globalStatus: GlobalStatus;
}

export interface MapState {
  header: HeaderData;
  nodes: MapNodeData[];
  connections: ConnectionData[];
}

export const mockMapState: MapState = {
  header: {
    simulationName: "The Schism",
    factions: ["NEW SYSTEM", "HUMAN COLLECTIVE"],
    day: 42,
    actionPoints: 12,
    globalStatus: "stable"
  },
  nodes: [
    {
      id: "core",
      type: "core",
      label: "CORE WORLDS",
      position: { x: 200, y: 200 },
      size: "large",
      status: "stable"
    },
    {
      id: "deep",
      type: "deep",
      label: "DEEP SPACE",
      position: { x: 600, y: 200 },
      size: "medium",
      status: "stable"
    },
    {
      id: "contested",
      type: "contested",
      label: "CONTESTED SYSTEM",
      position: { x: 1000, y: 200 },
      size: "medium",
      status: "warning"
    }
  ],
  connections: [
    { 
      id: "c1", 
      from: "core", 
      to: "deep", 
      status: "active",
      flowDirection: "forward"
    },
    { 
      id: "c2", 
      from: "deep", 
      to: "contested", 
      status: "active",
      flowDirection: "forward"
    },
    { 
      id: "c3", 
      from: "core", 
      to: "contested", 
      status: "disrupted",
      flowDirection: "forward"
    }
  ]
};
