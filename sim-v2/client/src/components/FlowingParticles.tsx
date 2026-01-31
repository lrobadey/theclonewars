import type { MapNodeData, ConnectionData } from '../data/mapFromGameState';

type NodeType = MapNodeData['type'];
type ConnectionStatus = ConnectionData['status'];

interface FlowingParticlesProps {
  pathId: string;
  sourceType: NodeType;
  status: ConnectionStatus;
}

// Get particle color based on source node type
function getParticleColor(type: NodeType): string {
  switch (type) {
    case 'core': return '#00D4FF';
    case 'deep': return '#FFB800';
    case 'contested': return '#FF3B3B';
  }
}

// Generate staggered particles along a path
function generateParticles(
  pathId: string, 
  color: string, 
  count: number,
  isActive: boolean
): React.ReactNode[] {
  if (!isActive) return [];
  
  const particles: React.ReactNode[] = [];
  const baseDuration = 4; // seconds for full path traversal
  
  for (let i = 0; i < count; i++) {
    const delay = (i / count) * baseDuration;
    // Vary particle sizes more for organic feel
    const size = 3 + Math.random() * 2; // 3 to 5 radius
    const glowOpacity = 0.5 + Math.random() * 0.4; // 0.5 to 0.9
    // Vary speed slightly for more organic movement
    const speedVariation = baseDuration + (Math.random() - 0.5) * 0.8; // +/- 0.4s
    const trailLength = 12 + Math.random() * 8; // 12 to 20px trail
    
    // Create cargo ship styled particles (elongated) for some particles
    const isCargoShip = i % 3 === 0;
    
    particles.push(
      <g key={`particle-${pathId}-${i}`}>
        {/* Comet trail effect */}
        <ellipse 
          rx={trailLength} 
          ry={size * 0.6} 
          fill={`url(#particle-trail-gradient-${i})`}
          opacity={0.4}
        >
          <animateMotion
            dur={`${speedVariation}s`}
            repeatCount="indefinite"
            begin={`${delay}s`}
            rotate="auto"
          >
            <mpath href={`#${pathId}`} />
          </animateMotion>
        </ellipse>
        
        {/* Outer glow */}
        <circle r={size + 4} fill={color} opacity={0.2}>
          <animateMotion
            dur={`${speedVariation}s`}
            repeatCount="indefinite"
            begin={`${delay}s`}
          >
            <mpath href={`#${pathId}`} />
          </animateMotion>
        </circle>
        
        {/* Main particle - elongated for cargo ships */}
        {isCargoShip ? (
          <ellipse 
            rx={size * 1.5} 
            ry={size * 0.8} 
            fill={color} 
            opacity={glowOpacity}
            className="flow-particle"
          >
            <animateMotion
              dur={`${speedVariation}s`}
              repeatCount="indefinite"
              begin={`${delay}s`}
              rotate="auto"
            >
              <mpath href={`#${pathId}`} />
            </animateMotion>
          </ellipse>
        ) : (
          <circle 
            r={size} 
            fill={color} 
            opacity={glowOpacity}
            className="flow-particle"
          >
            <animateMotion
              dur={`${speedVariation}s`}
              repeatCount="indefinite"
              begin={`${delay}s`}
            >
              <mpath href={`#${pathId}`} />
            </animateMotion>
          </circle>
        )}
        
        {/* Inner bright core */}
        <circle r={size * 0.4} fill="white" opacity={0.8}>
          <animateMotion
            dur={`${speedVariation}s`}
            repeatCount="indefinite"
            begin={`${delay}s`}
          >
            <mpath href={`#${pathId}`} />
          </animateMotion>
        </circle>
        
        {/* Sparkle effect at front of particle */}
        <circle r={size * 0.2} fill="white" opacity={0}>
          <animateMotion
            dur={`${speedVariation}s`}
            repeatCount="indefinite"
            begin={`${delay}s`}
          >
            <mpath href={`#${pathId}`} />
          </animateMotion>
          <animate
            attributeName="opacity"
            values="0;1;0"
            dur="0.5s"
            repeatCount="indefinite"
          />
        </circle>
      </g>
    );
  }
  
  return particles;
}

export function FlowingParticles({ pathId, sourceType, status }: FlowingParticlesProps) {
  const color = getParticleColor(sourceType);
  const isActive = status === 'active';
  const particleCount = isActive ? 5 : status === 'disrupted' ? 2 : 0;
  
  return (
    <g className="flowing-particles">
      {/* Trail gradient definitions */}
      <defs>
        {Array.from({ length: particleCount }).map((_, i) => (
          <linearGradient 
            key={`trail-grad-${i}`} 
            id={`particle-trail-gradient-${i}`} 
            x1="0%" 
            y1="0%" 
            x2="100%" 
            y2="0%"
          >
            <stop offset="0%" stopColor={color} stopOpacity="0" />
            <stop offset="50%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.6" />
          </linearGradient>
        ))}
      </defs>
      
      {generateParticles(pathId, color, particleCount, isActive || status === 'disrupted')}
    </g>
  );
}
