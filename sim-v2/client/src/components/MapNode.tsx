import { motion } from 'framer-motion';
import type { MapNodeData, NodeType, NodeSize } from '../data/mockMapData';

interface MapNodeProps {
  data: MapNodeData;
}

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

// Warning icon for contested nodes
function WarningIcon({ x, y, color }: { x: number; y: number; color: string }) {
  return (
    <motion.g
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      {/* Triangle background */}
      <motion.path
        d={`M ${x} ${y - 15} L ${x + 13} ${y + 10} L ${x - 13} ${y + 10} Z`}
        fill="none"
        stroke={color}
        strokeWidth="2"
        animate={{ opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* Exclamation mark */}
      <motion.line
        x1={x} y1={y - 8}
        x2={x} y2={y + 2}
        stroke={color}
        strokeWidth="2.5"
        strokeLinecap="round"
        animate={{ opacity: [0.8, 1, 0.8] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.circle
        cx={x} cy={y + 7}
        r="2"
        fill={color}
        animate={{ opacity: [0.8, 1, 0.8] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      />
    </motion.g>
  );
}

export function MapNode({ data }: MapNodeProps) {
  const { position, type, label, size = 'medium', status } = data;
  const { x, y } = position;
  const colors = getNodeColors(type);
  const dimensions = getNodeSize(size);
  
  const isContested = type === 'contested';
  const isLarge = size === 'large';

  return (
    <motion.g
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.8, ease: "easeOut" }}
    >
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
          opacity: [0.3, 0.5, 0.3],
          scale: [1, 1.02, 1]
        }}
        transition={{ 
          duration: 3, 
          repeat: Infinity, 
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

      {/* Warning icon for contested nodes */}
      {isContested && status === 'warning' && (
        <WarningIcon x={x} y={y} color={colors.primary} />
      )}

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
    </motion.g>
  );
}
