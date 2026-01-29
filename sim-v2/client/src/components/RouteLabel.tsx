import { motion } from 'framer-motion';
import type { ConnectionStatus } from '../data/mockMapData';

interface RouteLabelProps {
  pathId: string;
  status: ConnectionStatus;
}

// Get label text based on status
function getLabelText(status: ConnectionStatus): string {
  switch (status) {
    case 'active': return 'SUPPLY ROUTE ACTIVE';
    case 'disrupted': return 'ROUTE DISRUPTED';
    case 'blocked': return 'ROUTE BLOCKED';
  }
}

// Get label color based on status
function getLabelColor(status: ConnectionStatus): string {
  switch (status) {
    case 'active': return 'rgba(139, 164, 180, 0.8)'; // text-secondary
    case 'disrupted': return 'rgba(255, 184, 0, 0.8)'; // warning amber
    case 'blocked': return 'rgba(255, 59, 59, 0.8)'; // alert red
  }
}

export function RouteLabel({ pathId, status }: RouteLabelProps) {
  const labelText = getLabelText(status);
  const labelColor = getLabelColor(status);
  
  return (
    <motion.text
      className="route-label"
      fill={labelColor}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.8, delay: 1.5 }}
    >
      <textPath
        href={`#${pathId}`}
        startOffset="50%"
        textAnchor="middle"
        dominantBaseline="middle"
      >
        {labelText}
      </textPath>
    </motion.text>
  );
}
