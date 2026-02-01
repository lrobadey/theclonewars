import type { GameStateResponse } from '../api/types';

interface StatusHeaderProps {
  state: GameStateResponse;
}

function getGlobalStatus(state: GameStateResponse): 'stable' | 'alert' | 'critical' {
  // Simple heuristic for now
  if (state.contestedPlanet.control < 0.3) return 'critical';
  if (state.contestedPlanet.control < 0.6) return 'alert';
  return 'stable';
}

export function StatusHeader({ state }: StatusHeaderProps) {
  const globalStatus = getGlobalStatus(state);
  
  return (
    <header className="status-header fixed top-0 left-0 right-0 z-50 px-6 py-3">
      <div className="flex items-center justify-center gap-2 font-sans text-sm tracking-widest">
        <span className="text-text-primary font-bold">
          THE SCHISM
        </span>
        
        <span className="status-divider">//</span>
        
        <span className="text-core">
          THE NEW SYSTEM
        </span>
        <span className="text-text-secondary">vs</span>
        <span className="text-contested">
          THE HUMAN COLLECTIVE
        </span>
        
        <span className="status-divider">//</span>
        
        <span className="text-text-secondary">DAY:</span>
        <span className="text-deep font-bold">
          {String(state.day).padStart(3, '0')}
        </span>
        
        <span className="status-divider">//</span>
        
        <span className="text-text-secondary">AP:</span>
        <span className="text-text-primary font-bold">
          {state.actionPoints}
        </span>
        
        <span className="status-divider">//</span>
        
        <span className="text-text-secondary">GLOBAL STATUS:</span>
        <span className={`font-bold uppercase status-${globalStatus}`}>
          {globalStatus}
        </span>
      </div>
    </header>
  );
}
