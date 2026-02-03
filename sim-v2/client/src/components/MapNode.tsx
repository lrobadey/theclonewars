import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import type { MapNodeData } from '../data/mapFromGameState';

interface MapNodeProps {
  data: MapNodeData;
  isSelected?: boolean;
  onNodeClick?: (nodeId: string) => void;
}

type NodeType = MapNodeData['type'];
type NodeSize = MapNodeData['size'];

// Get colors based on node type
function getNodeColors(type: NodeType) {
  switch (type) {
    case 'core':
      return {
        primary: '#00D4FF',
        secondary: 'rgba(0, 212, 255, 0.5)',
        dim: 'rgba(0, 212, 255, 0.15)',
        gradient: 'url(#core-gradient)',
        filter: 'url(#glow-core)'
      };
    case 'deep':
      return {
        primary: '#FFB800',
        secondary: 'rgba(255, 184, 0, 0.5)',
        dim: 'rgba(255, 184, 0, 0.15)',
        gradient: 'url(#deep-gradient)',
        filter: 'url(#glow-deep)'
      };
    case 'contested':
      return {
        primary: '#FF3B3B',
        secondary: 'rgba(255, 59, 59, 0.5)',
        dim: 'rgba(255, 59, 59, 0.15)',
        gradient: 'url(#contested-gradient)',
        filter: 'url(#glow-contested)'
      };
  }
}

// Get size dimensions
function getNodeSize(size: NodeSize = 'medium') {
  switch (size) {
    case 'large':
      return { 
        innerRadius: 45, 
        outerRadius: 65, 
        glowRadius: 85,
        strokeWidth: 3,
        labelOffset: 95
      };
    case 'medium':
      return { 
        innerRadius: 35, 
        outerRadius: 50, 
        glowRadius: 65,
        strokeWidth: 2.5,
        labelOffset: 80
      };
    case 'small':
      return { 
        innerRadius: 25, 
        outerRadius: 38, 
        glowRadius: 50,
        strokeWidth: 2,
        labelOffset: 65
      };
  }
}

// Circuit tendril paths for large nodes
function generateTendrils(x: number, y: number, type: NodeType): React.ReactNode[] {
  if (type !== 'core') return [];
  
  const tendrils = [
    // Left tendrils
    { d: `M ${x - 65} ${y - 15} L ${x - 90} ${y - 15} L ${x - 90} ${y - 35}`, delay: 0 },
    { d: `M ${x - 65} ${y} L ${x - 100} ${y}`, delay: 0.2 },
    { d: `M ${x - 65} ${y + 15} L ${x - 85} ${y + 15} L ${x - 85} ${y + 30}`, delay: 0.4 },
    // Small dots at tendril ends
  ];
  
  return tendrils.map((tendril, i) => (
    <motion.path
      key={`tendril-${i}`}
      d={tendril.d}
      className="circuit-tendril"
      stroke="#00D4FF"
      strokeWidth="2"
      initial={{ pathLength: 0, opacity: 0 }}
      animate={{ pathLength: 1, opacity: 0.6 }}
      transition={{ 
        duration: 1.5, 
        delay: tendril.delay,
        ease: "easeOut"
      }}
    />
  ));
}

export function MapNode({ data, isSelected, onNodeClick }: MapNodeProps) {
  const { id, type, label, size = 'medium', x, y, isLabeled, subtitle1, subtitle2, severity } = data;
  const colors = getNodeColors(type);
  const dimensions = getNodeSize(size);
  const [isHovered, setIsHovered] = useState(false);
  const [pulseKey, setPulseKey] = useState(0);
  
  const isLarge = size === 'large';
  const isClickable = isLabeled; // requirement: only major nodes with labels are clickable

  const handleClick = () => {
    if (isClickable && onNodeClick) {
      onNodeClick(id);
      setPulseKey(prev => prev + 1);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick();
    }
  };

  const handleMouseEnter = () => {
    if (isClickable) setIsHovered(true);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
  };

  const severityColor =
    severity === 'danger' ? '#FF3B3B' : severity === 'warn' ? '#FFB800' : '#00D4FF';

  return (
    <motion.g
      initial={{ scale: 0, opacity: 0 }}
      animate={{ 
        scale: isSelected ? 1.05 : isHovered ? 1.08 : 1, 
        opacity: 1 
      }}
      transition={{ duration: 0.8, ease: "easeOut" }}
      onClick={isClickable ? handleClick : undefined}
      onKeyDown={isClickable ? handleKeyDown : undefined}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={isClickable ? 'cursor-pointer outline-none' : ''}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
    >
      {/* Selected highlight glow */}
      {isSelected && (
        <motion.circle
          cx={x}
          cy={y}
          r={dimensions.glowRadius + 15}
          fill="none"
          stroke={colors.primary}
          strokeWidth="2"
          initial={{ opacity: 0 }}
          animate={{ opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 2, repeat: Infinity }}
          filter="blur(8px)"
        />
      )}

      {/* One-time selection pulse ring */}
      {pulseKey > 0 && (
        <motion.circle
          key={`pulse-${pulseKey}`}
          cx={x}
          cy={y}
          r={dimensions.glowRadius}
          fill="none"
          stroke={colors.primary}
          strokeWidth="2"
          initial={{ opacity: 0.7, r: dimensions.glowRadius }}
          animate={{ opacity: 0, r: dimensions.glowRadius + 55 }}
          transition={{ duration: 0.65, ease: 'easeOut' }}
        />
      )}

      {/* Enhanced pulse rings for contested nodes or when hovered */}
      {(type === 'contested' || isHovered) && (
        <>
          <motion.circle
            cx={x}
            cy={y}
            r={dimensions.glowRadius}
            fill="none"
            stroke={colors.primary}
            strokeWidth="2"
            opacity={0}
            animate={{ 
              r: [dimensions.glowRadius, dimensions.glowRadius + 40],
              opacity: [0.6, 0]
            }}
            transition={{ 
              duration: 2, 
              repeat: Infinity,
              ease: "easeOut"
            }}
          />
          <motion.circle
            cx={x}
            cy={y}
            r={dimensions.glowRadius}
            fill="none"
            stroke={colors.primary}
            strokeWidth="2"
            opacity={0}
            animate={{ 
              r: [dimensions.glowRadius, dimensions.glowRadius + 40],
              opacity: [0.6, 0]
            }}
            transition={{ 
              duration: 2, 
              repeat: Infinity,
              ease: "easeOut",
              delay: 1
            }}
          />
        </>
      )}

      {/* Shield effect for core node */}
      {type === 'core' && (
        <motion.circle
          cx={x}
          cy={y}
          r={dimensions.outerRadius + 15}
          fill="none"
          stroke={colors.primary}
          strokeWidth="1"
          strokeDasharray="4 8"
          opacity={isHovered ? 0.6 : 0.3}
          animate={{ 
            rotate: 360,
            opacity: isHovered ? 0.6 : [0.3, 0.5, 0.3]
          }}
          transition={{ 
            rotate: { duration: 40, repeat: Infinity, ease: "linear" },
            opacity: { duration: 3, repeat: Infinity, ease: "easeInOut" }
          }}
          style={{ transformOrigin: `${x}px ${y}px` }}
        />
      )}

      {/* Warning beacon for contested node */}
      {type === 'contested' && (
        <motion.circle
          cx={x}
          cy={y}
          r={dimensions.innerRadius - 10}
          fill={colors.primary}
          opacity={0}
          animate={{ 
            opacity: [0, 0.8, 0]
          }}
          transition={{ 
            duration: 1.5, 
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      )}

      {/* Layer 1: Outer glow ring (largest, most diffuse) */}
      <motion.circle
        cx={x}
        cy={y}
        r={dimensions.glowRadius}
        fill="none"
        stroke={colors.dim}
        strokeWidth="1"
        filter={colors.filter}
        animate={{ 
          opacity: isSelected || isHovered ? 0.7 : [0.3, 0.5, 0.3],
          scale: isSelected || isHovered ? 1.05 : [1, 1.02, 1]
        }}
        transition={{ 
          duration: 3, 
          repeat: isSelected || isHovered ? 0 : Infinity, 
          ease: "easeInOut" 
        }}
      />

      {/* Layer 2: Outer decorative ring */}
      <motion.circle
        cx={x}
        cy={y}
        r={dimensions.outerRadius}
        fill="none"
        stroke={colors.secondary}
        strokeWidth={dimensions.strokeWidth}
        strokeDasharray={isLarge ? "8 4" : "6 3"}
        style={{ transformOrigin: `${x}px ${y}px` }}
        animate={{ rotate: 360 }}
        transition={{ 
          duration: isLarge ? 30 : 20, 
          repeat: Infinity, 
          ease: "linear" 
        }}
      />

      {/* Layer 2b: Second ring for large nodes (double-ring effect) */}
      {isLarge && (
        <motion.circle
          cx={x}
          cy={y}
          r={dimensions.outerRadius + 10}
          fill="none"
          stroke={colors.dim}
          strokeWidth="1.5"
          strokeDasharray="12 8"
          style={{ transformOrigin: `${x}px ${y}px` }}
          animate={{ rotate: -360 }}
          transition={{ 
            duration: 45, 
            repeat: Infinity, 
            ease: "linear" 
          }}
        />
      )}

      {/* Layer 3: Middle orbit ring */}
      <motion.circle
        cx={x}
        cy={y}
        r={dimensions.innerRadius + 8}
        fill="none"
        stroke={colors.secondary}
        strokeWidth="1"
        animate={{ 
          opacity: [0.4, 0.7, 0.4] 
        }}
        transition={{ 
          duration: 2.5, 
          repeat: Infinity, 
          ease: "easeInOut" 
        }}
      />

      {/* Layer 4: Inner filled circle with gradient */}
      <motion.circle
        cx={x}
        cy={y}
        r={dimensions.innerRadius}
        fill={colors.gradient}
        stroke={colors.primary}
        strokeWidth={dimensions.strokeWidth}
        filter={colors.filter}
        animate={{ 
          scale: [1, 1.02, 1],
        }}
        transition={{ 
          duration: 3, 
          repeat: Infinity, 
          ease: "easeInOut" 
        }}
      />

      {/* Layer 4b: Inner highlight */}
      <circle
        cx={x - dimensions.innerRadius * 0.3}
        cy={y - dimensions.innerRadius * 0.3}
        r={dimensions.innerRadius * 0.2}
        fill="rgba(255, 255, 255, 0.3)"
      />

      {/* Layer 5: Center dot */}
      <motion.circle
        cx={x}
        cy={y}
        r={4}
        fill={colors.primary}
        animate={{ 
          opacity: [0.8, 1, 0.8],
          scale: [1, 1.2, 1]
        }}
        transition={{ 
          duration: 2, 
          repeat: Infinity, 
          ease: "easeInOut" 
        }}
      />

      {/* Circuit tendrils for large nodes */}
      {isLarge && generateTendrils(x, y, type)}

      {/* Node Label (only show if there's a label) */}
      {label && (
        <motion.text
          x={x}
          y={y + dimensions.labelOffset}
          className="map-node-label"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          {label}
        </motion.text>
      )}

      {/* Hover Tooltip */}
      <AnimatePresence>
        {isHovered && isClickable && (
          <motion.g
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {/* Tooltip background */}
            <rect
              x={x - 60}
              y={y - dimensions.outerRadius - 60}
              width="120"
              height={subtitle2 ? 62 : 52}
              rx="8"
              fill="rgba(10, 14, 20, 0.95)"
              stroke={colors.primary}
              strokeWidth="1"
              filter="url(#route-glow)"
            />
            
            {/* Tooltip title */}
            <text
              x={x}
              y={y - dimensions.outerRadius - 42}
              textAnchor="middle"
              fill={colors.primary}
              fontSize="12"
              fontWeight="bold"
              style={{ fontFamily: 'Space Mono, monospace' }}
            >
              {label}
            </text>
            
            {/* Tooltip status */}
            <text
              x={x}
              y={y - dimensions.outerRadius - 26}
              textAnchor="middle"
              fill="#8BA4B4"
              fontSize="10"
              style={{ fontFamily: 'Space Mono, monospace' }}
            >
              {subtitle1}
            </text>

            {subtitle2 && (
              <text
                x={x}
                y={y - dimensions.outerRadius - 14}
                textAnchor="middle"
                fill="#8BA4B4"
                fontSize="9"
                opacity="0.8"
                style={{ fontFamily: 'Space Mono, monospace' }}
              >
                {subtitle2}
              </text>
            )}

            {/* Tooltip severity dot */}
            <circle
              cx={x - 52}
              cy={y - dimensions.outerRadius - 42}
              r="3"
              fill={severityColor}
            />
          </motion.g>
        )}
      </AnimatePresence>
    </motion.g>
  );
}
