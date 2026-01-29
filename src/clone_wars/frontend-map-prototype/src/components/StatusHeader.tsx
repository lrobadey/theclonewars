import type { HeaderData, GlobalStatus } from '../data/mockMapData';

interface StatusHeaderProps {
  data: HeaderData;
}

function getStatusClass(status: GlobalStatus): string {
  switch (status) {
    case 'stable': return 'status-stable';
    case 'alert': return 'status-alert';
    case 'critical': return 'status-critical';
    default: return 'status-stable';
  }
}

export function StatusHeader({ data }: StatusHeaderProps) {
  return (
    <header className="status-header fixed top-0 left-0 right-0 z-50 px-6 py-3">
      <div className="flex items-center justify-center gap-2 font-mono text-sm tracking-widest">
        <span className="text-text-primary font-bold">
          {data.simulationName}
        </span>
        
        <span className="status-divider">//</span>
        
        <span className="text-core">
          {data.factions[0]}
        </span>
        <span className="text-text-secondary">vs</span>
        <span className="text-contested">
          {data.factions[1]}
        </span>
        
        <span className="status-divider">//</span>
        
        <span className="text-text-secondary">DAY:</span>
        <span className="text-deep font-bold">
          {String(data.day).padStart(3, '0')}
        </span>
        
        <span className="status-divider">//</span>
        
        <span className="text-text-secondary">AP:</span>
        <span className="text-text-primary font-bold">
          {data.actionPoints}
        </span>
        
        <span className="status-divider">//</span>
        
        <span className="text-text-secondary">GLOBAL STATUS:</span>
        <span className={`font-bold uppercase ${getStatusClass(data.globalStatus)}`}>
          {data.globalStatus}
        </span>
      </div>
    </header>
  );
}
