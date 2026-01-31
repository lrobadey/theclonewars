import React, { useMemo } from 'react';

interface Star {
  id: number;
  x: number;
  y: number;
  size: number;
  opacity: number;
  twinkleDelay: number;
  twinkleDuration: number;
}

interface StarfieldProps {
  width: number;
  height: number;
  starCount?: number;
}

export const Starfield: React.FC<StarfieldProps> = ({ 
  width, 
  height, 
  starCount = 150 
}) => {
  const stars = useMemo(() => {
    const generatedStars: Star[] = [];
    
    for (let i = 0; i < starCount; i++) {
      generatedStars.push({
        id: i,
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * 2 + 0.5, // 0.5 to 2.5px
        opacity: Math.random() * 0.6 + 0.2, // 0.2 to 0.8
        twinkleDelay: Math.random() * 5, // 0 to 5s delay
        twinkleDuration: Math.random() * 3 + 2, // 2 to 5s duration
      });
    }
    
    return generatedStars;
  }, [width, height, starCount]);

  // Generate shooting stars (fewer, bigger effect)
  const shootingStars = useMemo(() => {
    const shooting: Array<{
      id: number;
      x: number;
      y: number;
      angle: number;
      delay: number;
      duration: number;
    }> = [];
    
    for (let i = 0; i < 3; i++) {
      shooting.push({
        id: i,
        x: Math.random() * width * 0.5, // Start from left side
        y: Math.random() * height,
        angle: Math.random() * 30 - 15, // -15 to +15 degrees
        delay: Math.random() * 20 + 5, // 5 to 25s delay
        duration: Math.random() * 2 + 1, // 1 to 3s duration
      });
    }
    
    return shooting;
  }, [width, height]);

  return (
    <g className="starfield">
      {/* Background stars with twinkling */}
      {stars.map((star) => (
        <circle
          key={`star-${star.id}`}
          cx={star.x}
          cy={star.y}
          r={star.size}
          fill="white"
          opacity={star.opacity}
          style={{
            animation: `twinkle ${star.twinkleDuration}s ease-in-out ${star.twinkleDelay}s infinite`,
          }}
        />
      ))}
      
      {/* Shooting stars */}
      {shootingStars.map((shooting) => (
        <g key={`shooting-${shooting.id}`}>
          <line
            x1={shooting.x}
            y1={shooting.y}
            x2={shooting.x + 80 * Math.cos((shooting.angle * Math.PI) / 180)}
            y2={shooting.y + 80 * Math.sin((shooting.angle * Math.PI) / 180)}
            stroke="url(#shootingStarGradient)"
            strokeWidth="2"
            strokeLinecap="round"
            opacity="0"
            style={{
              animation: `shootingStar ${shooting.duration}s linear ${shooting.delay}s infinite`,
            }}
          />
        </g>
      ))}
      
      {/* Gradient for shooting stars */}
      <defs>
        <linearGradient id="shootingStarGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="white" stopOpacity="0" />
          <stop offset="50%" stopColor="white" stopOpacity="0.8" />
          <stop offset="100%" stopColor="cyan" stopOpacity="1" />
        </linearGradient>
      </defs>
    </g>
  );
};
