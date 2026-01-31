import { motion } from 'framer-motion';
import { useState } from 'react';
import type { ConnectionData, MapNodeData } from '../data/mapFromGameState';

type NodeType = MapNodeData['type'];

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
  const toColor = getNodeColor(toNode.type);
  const [isHovered, setIsHovered] = useState(false);
  
  // Determine opacity and dash pattern based on status
  const isActive = status === 'active';
  const isDisrupted = status === 'disrupted';
  
  const baseOpacity = isActive ? 0.8 : isDisrupted ? 0.4 : 0.2;
  const dashArray = isActive ? "12 6" : isDisrupted ? "8 12" : "4 16";
  const hoverOpacity = Math.min(baseOpacity + 0.3, 1);
  
  return (
    <g 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ cursor: 'pointer' }}
    >
      {/* Outer hyperspace lane border (left) */}
      <motion.path
        d={path}
        fill="none"
        stroke={fromColor}
        strokeWidth="1"
        strokeLinecap="round"
        opacity={isHovered ? 0.5 : 0.2}
        transform="translate(-6, 0)"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5, ease: "easeOut", delay: 0.1 }}
      />
      
      {/* Outer hyperspace lane border (right) */}
      <motion.path
        d={path}
        fill="none"
        stroke={toColor}
        strokeWidth="1"
        strokeLinecap="round"
        opacity={isHovered ? 0.5 : 0.2}
        transform="translate(6, 0)"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5, ease: "easeOut", delay: 0.1 }}
      />
      
      {/* Background glow path - enhanced on hover */}
      <motion.path
        d={path}
        fill="none"
        stroke={fromColor}
        strokeWidth={isHovered ? "16" : "8"}
        strokeLinecap="round"
        opacity={isHovered ? 0.3 : 0.15}
        filter="url(#route-glow)"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ 
          pathLength: { duration: 1.5, ease: "easeOut" },
          strokeWidth: { duration: 0.3 },
          opacity: { duration: 0.3 }
        }}
      />
      
      {/* Main route path with gradient */}
      <motion.path
        d={path}
        fill="none"
        stroke={`url(#${getGradientId(fromNode.type, toNode.type)})`}
        strokeWidth={isHovered ? "4" : "3"}
        strokeLinecap="round"
        strokeDasharray={dashArray}
        opacity={isHovered ? hoverOpacity : baseOpacity}
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ 
          pathLength: 1, 
          opacity: isHovered ? hoverOpacity : baseOpacity,
          strokeDashoffset: isActive ? [0, -36] : 0
        }}
        transition={{ 
          pathLength: { duration: 1.5, ease: "easeOut" },
          opacity: { duration: 0.3 },
          strokeWidth: { duration: 0.3 },
          strokeDashoffset: { 
            duration: 2, 
            repeat: Infinity, 
            ease: "linear" 
          }
        }}
      />
      
      {/* Energy pulses along the route (only for active routes) */}
      {isActive && (
        <>
          <motion.circle
            r="3"
            fill="white"
            opacity={isHovered ? 0.9 : 0.6}
            filter="url(#route-glow)"
          >
            <animateMotion
              dur="3s"
              repeatCount="indefinite"
              path={path}
            />
          </motion.circle>
          <motion.circle
            r="3"
            fill="white"
            opacity={isHovered ? 0.9 : 0.6}
            filter="url(#route-glow)"
          >
            <animateMotion
              dur="3s"
              repeatCount="indefinite"
              path={path}
              begin="1.5s"
            />
          </motion.circle>
        </>
      )}
      
      {/* Inner bright line */}
      <motion.path
        d={path}
        fill="none"
        stroke="rgba(255, 255, 255, 0.3)"
        strokeWidth={isHovered ? "1.5" : "1"}
        strokeLinecap="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ 
          pathLength: { duration: 1.5, ease: "easeOut", delay: 0.3 },
          strokeWidth: { duration: 0.3 }
        }}
      />
      
      {/* Connection endpoints - small circles at junctions */}
      <motion.circle
        cx={fromNode.x}
        cy={fromNode.y}
        r={isHovered ? "5" : "4"}
        fill={fromColor}
        opacity={isHovered ? 0.9 : 0.6}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ 
          scale: { duration: 0.3, delay: 1.5 },
          r: { duration: 0.3 }
        }}
      />
      
      {/* Invisible interaction area for better hover detection */}
      <path
        d={path}
        fill="none"
        stroke="transparent"
        strokeWidth="20"
        strokeLinecap="round"
        pointerEvents="stroke"
      />
    </g>
  );
}
