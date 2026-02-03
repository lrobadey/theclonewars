import { useMemo } from 'react';
import type { MapConnection, MapNode } from '../api/types';
import { MapNode } from './MapNode';
import { SupplyRoute } from './SupplyRoute';
import { FlowingParticles } from './FlowingParticles';
import { RouteLabel } from './RouteLabel';
import { Starfield } from './Starfield';

interface StrategicMapProps {
  nodes: MapNode[];
  connections: MapConnection[];
  selectedNodeId?: string;
  onNodeClick?: (nodeId: string) => void;
}

// Generate a unique path ID for a connection
function getPathId(connectionId: string): string {
  return `route-path-${connectionId}`;
}

// Calculate Bezier control points for organic curves
function calculateBezierPath(
  from: { x: number; y: number },
  to: { x: number; y: number }
): string {
  const midX = (from.x + to.x) / 2;
  
  // Add some vertical offset for organic feel
  const offsetY = -30;
  
  // Control points for cubic Bezier
  const cp1x = from.x + (midX - from.x) * 0.5;
  const cp1y = from.y + offsetY;
  const cp2x = to.x - (to.x - midX) * 0.5;
  const cp2y = to.y + offsetY;
  
  return `M ${from.x} ${from.y} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${to.x} ${to.y}`;
}

export function StrategicMap({ nodes, connections, selectedNodeId, onNodeClick }: StrategicMapProps) {
  // Create a lookup map for nodes by ID
  const nodeMap = useMemo(() => {
    const map = new Map<string, MapNode>();
    nodes.forEach(node => map.set(node.id, node));
    return map;
  }, [nodes]);

  // Pre-calculate paths for connections
  const connectionPaths = useMemo(() => {
    return connections.map(conn => {
      const fromNode = nodeMap.get(conn.from);
      const toNode = nodeMap.get(conn.to);
      
      if (!fromNode || !toNode) return null;
      
      const path = calculateBezierPath(
        { x: fromNode.x, y: fromNode.y },
        { x: toNode.x, y: toNode.y }
      );
      const pathId = getPathId(conn.id);
      
      return {
        ...conn,
        path,
        pathId,
        fromNode,
        toNode
      };
    }).filter(Boolean);
  }, [connections, nodeMap]);

  return (
    <svg 
      viewBox="0 0 1200 400" 
      className="strategic-map"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Definitions for filters, gradients, and reusable elements */}
      <defs>
        {/* Glow filters for each node type */}
        <filter id="glow-core" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur1" />
          <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur2" />
          <feGaussianBlur in="SourceGraphic" stdDeviation="20" result="blur3" />
          <feMerge>
            <feMergeNode in="blur3" />
            <feMergeNode in="blur2" />
            <feMergeNode in="blur1" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        
        <filter id="glow-deep" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur1" />
          <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur2" />
          <feGaussianBlur in="SourceGraphic" stdDeviation="20" result="blur3" />
          <feMerge>
            <feMergeNode in="blur3" />
            <feMergeNode in="blur2" />
            <feMergeNode in="blur1" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        
        <filter id="glow-contested" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur1" />
          <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur2" />
          <feGaussianBlur in="SourceGraphic" stdDeviation="20" result="blur3" />
          <feMerge>
            <feMergeNode in="blur3" />
            <feMergeNode in="blur2" />
            <feMergeNode in="blur1" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Soft glow for route paths */}
        <filter id="route-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Gradients for node fills */}
        <radialGradient id="core-gradient" cx="30%" cy="30%">
          <stop offset="0%" stopColor="#00D4FF" stopOpacity="0.9" />
          <stop offset="50%" stopColor="#00A8CC" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#006688" stopOpacity="0.5" />
        </radialGradient>
        
        <radialGradient id="deep-gradient" cx="30%" cy="30%">
          <stop offset="0%" stopColor="#FFB800" stopOpacity="0.9" />
          <stop offset="50%" stopColor="#CC9200" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#886200" stopOpacity="0.5" />
        </radialGradient>
        
        <radialGradient id="contested-gradient" cx="30%" cy="30%">
          <stop offset="0%" stopColor="#FF3B3B" stopOpacity="0.9" />
          <stop offset="50%" stopColor="#CC2E2E" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#881F1F" stopOpacity="0.5" />
        </radialGradient>

        {/* Route path gradients */}
        <linearGradient id="route-gradient-core-deep" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00D4FF" />
          <stop offset="100%" stopColor="#FFB800" />
        </linearGradient>
        
        <linearGradient id="route-gradient-deep-contested" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#FFB800" />
          <stop offset="100%" stopColor="#FF3B3B" />
        </linearGradient>
        
        <linearGradient id="route-gradient-core-contested" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00D4FF" />
          <stop offset="100%" stopColor="#FF3B3B" />
        </linearGradient>

        {/* Define paths for animateMotion */}
        {connectionPaths.map(conn => conn && (
          <path 
            key={conn.pathId} 
            id={conn.pathId} 
            d={conn.path}
            fill="none"
          />
        ))}
      </defs>

      {/* Background rect for interactions */}
      <rect 
        className="strategic-map-bg" 
        width="100%" 
        height="100%" 
        fill="transparent"
      />

      {/* Layer 0: Starfield Background */}
      <Starfield width={1200} height={400} starCount={150} />

      {/* Layer 1: Supply Route Connections */}
      <g className="connections-layer">
        {connectionPaths.map(conn => conn && (
          <SupplyRoute
            key={conn.id}
            connection={conn}
            pathId={conn.pathId}
            path={conn.path}
          />
        ))}
      </g>

      {/* Layer 2: Route Labels (only for routes where source has a label) */}
      <g className="labels-layer">
        {connectionPaths.map(conn => {
          // Only show label if from node has a label (main node connection)
          if (!conn || !conn.fromNode.isLabeled) return null;
          return (
            <RouteLabel
              key={`label-${conn.id}`}
              pathId={conn.pathId}
              status={conn.status}
            />
          );
        })}
      </g>

      {/* Layer 3: Flowing Particles */}
      <g className="particles-layer">
        {connectionPaths.map(conn => conn && (
          <FlowingParticles
            key={`particles-${conn.id}`}
            pathId={conn.pathId}
            sourceType={conn.fromNode.type}
            status={conn.status}
          />
        ))}
      </g>

      {/* Layer 4: Map Nodes (on top) */}
      <g className="nodes-layer">
        {nodes.map(node => (
          <MapNode 
            key={node.id} 
            data={node} 
            isSelected={selectedNodeId === node.id}
            onNodeClick={onNodeClick}
          />
        ))}
      </g>
    </svg>
  );
}
