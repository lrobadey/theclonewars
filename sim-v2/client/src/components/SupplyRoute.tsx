import { motion } from 'framer-motion';
import type { ConnectionData, NodeType, MapNodeData } from '../data/mockMapData';

interface ExtendedConnectionData extends ConnectionData {
  fromNode: MapNodeData;
  toNode: MapNodeData;
}

interface SupplyRouteProps {
  connection: ExtendedConnectionData;
  pathId: string;
  path: string;
}

// Get gradient ID based on connection nodes
function getGradientId(fromType: NodeType, toType: NodeType): string {
  return `route-gradient-${fromType}-${toType}`;
}

// Get color based on node type
function getNodeColor(type: NodeType): string {
  switch (type) {
    case 'core': return '#00D4FF';
    case 'deep': return '#FFB800';
    case 'contested': return '#FF3B3B';
  }
}

export function SupplyRoute({ connection, path }: SupplyRouteProps) {
  const { status, fromNode, toNode } = connection;
  const fromColor = getNodeColor(fromNode.type);
  
  // Determine opacity and dash pattern based on status
  const isActive = status === 'active';
  const isDisrupted = status === 'disrupted';
  
  const baseOpacity = isActive ? 0.8 : isDisrupted ? 0.4 : 0.2;
  const dashArray = isActive ? "12 6" : isDisrupted ? "8 12" : "4 16";
  
  return (
    <g>
      {/* Background glow path */}
      <motion.path
        d={path}
        fill="none"
        stroke={fromColor}
        strokeWidth="8"
        strokeLinecap="round"
        opacity={0.15}
        filter="url(#route-glow)"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5, ease: "easeOut" }}
      />
      
      {/* Main route path with gradient */}
      <motion.path
        d={path}
        fill="none"
        stroke={`url(#${getGradientId(fromNode.type, toNode.type)})`}
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray={dashArray}
        opacity={baseOpacity}
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ 
          pathLength: 1, 
          opacity: baseOpacity,
          strokeDashoffset: isActive ? [0, -36] : 0
        }}
        transition={{ 
          pathLength: { duration: 1.5, ease: "easeOut" },
          opacity: { duration: 0.5 },
          strokeDashoffset: { 
            duration: 2, 
            repeat: Infinity, 
            ease: "linear" 
          }
        }}
      />
      
      {/* Inner bright line */}
      <motion.path
        d={path}
        fill="none"
        stroke="rgba(255, 255, 255, 0.3)"
        strokeWidth="1"
        strokeLinecap="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5, ease: "easeOut", delay: 0.3 }}
      />
      
      {/* Connection endpoints - small circles at junctions */}
      <motion.circle
        cx={fromNode.position.x}
        cy={fromNode.position.y}
        r="4"
        fill={fromColor}
        opacity={0.6}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ duration: 0.3, delay: 1.5 }}
      />
    </g>
  );
}
