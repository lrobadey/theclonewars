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
    </g>
  );
};
