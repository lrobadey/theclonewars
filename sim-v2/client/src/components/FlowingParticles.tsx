import { useMemo } from 'react';
import type { MapConnection, MapNode } from '../api/types';

type NodeType = MapNode['type'];
type ConnectionStatus = MapConnection['status'];

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
type ParticleSpec = {
  delay: number;
  size: number;
  glowOpacity: number;
  speed: number;
  trailLength: number;
  isCargoShip: boolean;
};

function createSeededRng(seed: string) {
  let hash = 2166136261;
  for (let i = 0; i < seed.length; i += 1) {
    hash ^= seed.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  let state = hash >>> 0;
  return () => {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    return (state >>> 0) / 4294967296;
  };
}

function buildParticleSpecs(pathId: string, count: number, baseDuration: number): ParticleSpec[] {
  const rng = createSeededRng(pathId);
  return Array.from({ length: count }).map((_, i) => {
    const delay = (i / count) * baseDuration;
    const size = 3 + rng() * 2;
    const glowOpacity = 0.5 + rng() * 0.4;
    const speed = baseDuration + (rng() - 0.5) * 0.8;
    const trailLength = 12 + rng() * 8;
    const isCargoShip = i % 3 === 0;

    return {
      delay,
      size,
      glowOpacity,
      speed,
      trailLength,
      isCargoShip,
    };
  });
}

function generateParticles(
  pathId: string,
  color: string,
  specs: ParticleSpec[],
  isActive: boolean
): React.ReactNode[] {
  if (!isActive) return [];

  return specs.map((spec, i) => (
    <g key={`particle-${pathId}-${i}`}>
      {/* Comet trail effect */}
      <ellipse 
        rx={spec.trailLength} 
        ry={spec.size * 0.6} 
        fill={`url(#particle-trail-gradient-${pathId}-${i})`}
        opacity={0.4}
      >
        <animateMotion
          dur={`${spec.speed}s`}
          repeatCount="indefinite"
          begin={`${spec.delay}s`}
          rotate="auto"
        >
          <mpath href={`#${pathId}`} />
        </animateMotion>
      </ellipse>
      
      {/* Outer glow */}
      <circle r={spec.size + 4} fill={color} opacity={0.2}>
        <animateMotion
          dur={`${spec.speed}s`}
          repeatCount="indefinite"
          begin={`${spec.delay}s`}
        >
          <mpath href={`#${pathId}`} />
        </animateMotion>
      </circle>
      
      {/* Main particle - elongated for cargo ships */}
      {spec.isCargoShip ? (
        <ellipse 
          rx={spec.size * 1.5} 
          ry={spec.size * 0.8} 
          fill={color} 
          opacity={spec.glowOpacity}
          className="flow-particle"
        >
          <animateMotion
            dur={`${spec.speed}s`}
            repeatCount="indefinite"
            begin={`${spec.delay}s`}
            rotate="auto"
          >
            <mpath href={`#${pathId}`} />
          </animateMotion>
        </ellipse>
      ) : (
        <circle 
          r={spec.size} 
          fill={color} 
          opacity={spec.glowOpacity}
          className="flow-particle"
        >
          <animateMotion
            dur={`${spec.speed}s`}
            repeatCount="indefinite"
            begin={`${spec.delay}s`}
          >
            <mpath href={`#${pathId}`} />
          </animateMotion>
        </circle>
      )}
      
      {/* Inner bright core */}
      <circle r={spec.size * 0.4} fill="white" opacity={0.8}>
        <animateMotion
          dur={`${spec.speed}s`}
          repeatCount="indefinite"
          begin={`${spec.delay}s`}
        >
          <mpath href={`#${pathId}`} />
        </animateMotion>
      </circle>
      
      {/* Sparkle effect at front of particle */}
      <circle r={spec.size * 0.2} fill="white" opacity={0}>
        <animateMotion
          dur={`${spec.speed}s`}
          repeatCount="indefinite"
          begin={`${spec.delay}s`}
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
  ));
}

export function FlowingParticles({ pathId, sourceType, status }: FlowingParticlesProps) {
  const color = getParticleColor(sourceType);
  const isActive = status === 'active';
  const particleCount = isActive ? 5 : status === 'disrupted' ? 2 : 0;
  const baseDuration = 4;
  const particleSpecs = useMemo(
    () => buildParticleSpecs(pathId, particleCount, baseDuration),
    [pathId, particleCount]
  );
  
  return (
    <g className="flowing-particles">
      {/* Trail gradient definitions */}
      <defs>
        {Array.from({ length: particleCount }).map((_, i) => (
          <linearGradient 
            key={`trail-grad-${i}`} 
            id={`particle-trail-gradient-${pathId}-${i}`} 
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
      
      {generateParticles(pathId, color, particleSpecs, isActive || status === 'disrupted')}
    </g>
  );
}
