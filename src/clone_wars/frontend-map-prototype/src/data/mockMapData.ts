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
    simulationName: "THE SCHISM SIMULATION",
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
      position: { x: 150, y: 200 },
      size: "large",
      status: "stable"
    },
    {
      id: "waypoint1",
      type: "core",
      label: "",
      position: { x: 300, y: 150 },
      size: "small",
      status: "stable"
    },
    {
      id: "waypoint2",
      type: "core",
      label: "",
      position: { x: 350, y: 250 },
      size: "small",
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
      id: "waypoint3",
      type: "deep",
      label: "",
      position: { x: 750, y: 280 },
      size: "small",
      status: "stable"
    },
    {
      id: "contested",
      type: "contested",
      label: "CONTESTED SYSTEM",
      position: { x: 1050, y: 250 },
      size: "medium",
      status: "warning"
    }
  ],
  connections: [
    { 
      id: "c1", 
      from: "core", 
      to: "waypoint1", 
      status: "active",
      flowDirection: "forward"
    },
    { 
      id: "c2", 
      from: "waypoint1", 
      to: "deep", 
      status: "active",
      flowDirection: "forward"
    },
    { 
      id: "c3", 
      from: "core", 
      to: "waypoint2", 
      status: "active",
      flowDirection: "forward"
    },
    { 
      id: "c4", 
      from: "waypoint2", 
      to: "deep", 
      status: "active",
      flowDirection: "forward"
    },
    { 
      id: "c5", 
      from: "deep", 
      to: "waypoint3", 
      status: "active",
      flowDirection: "forward"
    },
    { 
      id: "c6", 
      from: "waypoint3", 
      to: "contested", 
      status: "active",
      flowDirection: "forward"
    }
  ]
};
