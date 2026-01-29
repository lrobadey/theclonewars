import type { NodeType, ConnectionStatus } from '../data/mockMapData';

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
    const size = 3 + (i % 2); // Alternate between 3 and 4 radius
    const glowOpacity = 0.6 + (i % 3) * 0.15; // Vary glow intensity
    
    particles.push(
      <g key={`particle-${pathId}-${i}`}>
        {/* Outer glow */}
        <circle r={size + 4} fill={color} opacity={0.2}>
          <animateMotion
            dur={`${baseDuration}s`}
            repeatCount="indefinite"
            begin={`${delay}s`}
          >
            <mpath href={`#${pathId}`} />
          </animateMotion>
        </circle>
        
        {/* Main particle */}
        <circle 
          r={size} 
          fill={color} 
          opacity={glowOpacity}
          className="flow-particle"
        >
          <animateMotion
            dur={`${baseDuration}s`}
            repeatCount="indefinite"
            begin={`${delay}s`}
          >
            <mpath href={`#${pathId}`} />
          </animateMotion>
        </circle>
        
        {/* Inner bright core */}
        <circle r={size * 0.4} fill="white" opacity={0.8}>
          <animateMotion
            dur={`${baseDuration}s`}
            repeatCount="indefinite"
            begin={`${delay}s`}
          >
            <mpath href={`#${pathId}`} />
          </animateMotion>
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
      {generateParticles(pathId, color, particleCount, isActive || status === 'disrupted')}
    </g>
  );
}
