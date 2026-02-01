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

function formatTooltip(connection: ExtendedConnectionData): string {
  const travelDays = connection.aggregatedTravelDays ?? 0;
  const riskPct = Math.round((connection.risk ?? 0) * 100);
  const legs = connection.underlyingLegs ?? [];
  const legsText = legs.length
    ? legs.map(leg => `${leg.origin} → ${leg.destination}`).join(' | ')
    : `${connection.from} → ${connection.to}`;

  return [
    `Route: ${connection.from} → ${connection.to}`,
    `Risk: ${riskPct}%`,
    `Travel: ${travelDays} days`,
    `Legs: ${legsText}`,
  ].join('\n');
}

export function SupplyRoute({ connection, path }: SupplyRouteProps) {
  const { status, fromNode, toNode } = connection;
  const fromColor = getNodeColor(fromNode.type);
  const toColor = getNodeColor(toNode.type);
  const [isHovered, setIsHovered] = useState(false);
  
  // Determine opacity and dash pattern based on status
  const isActive = status === 'active';
  const isDisrupted = status === 'disrupted';
  const isBlocked = status === 'blocked';
  
  const baseOpacity = isActive ? 0.8 : isDisrupted ? 0.45 : 0.2;
  const dashArray = isActive ? "14 6" : isDisrupted ? "6 10" : "2 12";
  const hoverOpacity = Math.min(baseOpacity + 0.3, 1);
  const flowDuration = isActive ? 2 : isDisrupted ? 3.5 : 0;
  const pulseDuration = isActive ? "3s" : "4.5s";
  
  return (
    <g 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ cursor: 'pointer' }}
      className="supply-route-group"
    >
      <title>{formatTooltip(connection)}</title>
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
        strokeWidth={isHovered ? "4.5" : "3"}
        strokeLinecap="round"
        strokeDasharray={dashArray}
        opacity={isHovered ? hoverOpacity : baseOpacity}
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ 
          pathLength: 1, 
          opacity: isHovered ? hoverOpacity : baseOpacity,
          strokeDashoffset: isActive ? [0, -36] : isDisrupted ? [0, -18] : 0
        }}
        transition={{ 
          pathLength: { duration: 1.5, ease: "easeOut" },
          opacity: { duration: 0.3 },
          strokeWidth: { duration: 0.3 },
          strokeDashoffset: { 
            duration: flowDuration || 0.01,
            repeat: flowDuration ? Infinity : 0,
            ease: "linear"
          }
        }}
      />
      
      {/* Energy pulses along the route (only for active routes) */}
      {!isBlocked && (
        <>
          <motion.polygon
            points="0,-4 8,0 0,4"
            fill="white"
            opacity={isActive ? 0.8 : 0.4}
            filter="url(#route-glow)"
          >
            <animateMotion
              dur={pulseDuration}
              repeatCount="indefinite"
              path={path}
              rotate="auto"
            />
          </motion.polygon>
          <motion.circle
            r={isActive ? "3" : "2"}
            fill="white"
            opacity={isHovered ? 0.9 : 0.5}
            filter="url(#route-glow)"
          >
            <animateMotion
              dur={pulseDuration}
              repeatCount="indefinite"
              path={path}
              begin="1.5s"
            />
          </motion.circle>
        </>
      )}
      
      {/* Blocked route warning pulse */}
      {isBlocked && (
        <motion.circle
          r="6"
          fill="rgba(255, 59, 59, 0.6)"
          opacity={0.6}
          filter="url(#route-glow)"
        >
          <animateMotion
            dur="6s"
            repeatCount="indefinite"
            path={path}
            begin="0s"
          />
          <animate
            attributeName="r"
            values="4;8;4"
            dur="1.5s"
            repeatCount="indefinite"
          />
        </motion.circle>
      )}
      
      {/* Inner bright line */}
      <motion.path
        d={path}
        fill="none"
        stroke="rgba(255, 255, 255, 0.35)"
        strokeWidth={isHovered ? "1.6" : "1"}
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
