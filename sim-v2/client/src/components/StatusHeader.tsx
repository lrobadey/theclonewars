import type { GameStateResponse } from '../api/types';

interface StatusHeaderProps {
  state: GameStateResponse;
}

export function StatusHeader({ state }: StatusHeaderProps) {
  const control = Math.round(state.contestedPlanet.control * 100);
  const phase = state.operation?.currentPhase ? state.operation.currentPhase.replace(/_/g, ' ') : 'idle';
  
  return (
    <header className="status-header glass-surface glass-blur glass-tone-deep glass-elev-mid glass-highlight fixed top-0 left-0 right-0 z-50 px-4 py-3 md:px-6">
      <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 font-sans text-[11px] md:text-sm tracking-[0.18em] uppercase">
        <span className="text-text-primary font-bold">
          THE SCHISM
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

        <span className="text-text-secondary">CONTROL:</span>
        <span className="text-contested font-bold">
          {control}%
        </span>

        <span className="status-divider">//</span>

        <span className="text-text-secondary">OP:</span>
        <span className="text-core font-bold">
          {phase}
        </span>
      </div>
    </header>
  );
}
