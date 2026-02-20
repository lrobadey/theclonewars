import { useState } from 'react';
import type { ApiResponse, CatalogResponse, GameStateResponse } from '../../api/types';
import { Chip } from './ui/Chip';
import { CollapsibleModule } from './ui/CollapsibleModule';

interface ContestedSystemBarProps {
  state: GameStateResponse;
  catalog: CatalogResponse | null;
  onActionResult: (resp: ApiResponse) => void;
}

export function ContestedSystemBar({ state }: ContestedSystemBarProps) {
  const [sections, setSections] = useState({
    summary: true,
    expert: false,
  });

  const toggle = (key: keyof typeof sections) => {
    setSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="p-4 md:p-6">
      <div className="nodebar-modules">
        <CollapsibleModule
          id="contested-summary"
          title="Campaign Command Surface"
          tone="contested"
          isOpen={sections.summary}
          onToggle={() => toggle('summary')}
          summary="Use dedicated campaign UI from map selection"
        >
          <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-4 space-y-3">
            <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
              Contested operations are now managed in the full command surface.
            </div>
            <div className="text-sm text-text-primary">
              Close this drawer, select CONTESTED SYSTEM on the map, and use the integrated campaign flow (Prepare, Execute, Debrief, Adapt).
            </div>
            <div className="flex flex-wrap gap-2">
              <Chip label={`Control ${Math.round(state.contestedPlanet.control * 100)}%`} tone="warn" />
              <Chip label={`Intel ${Math.round(state.contestedPlanet.enemy.intelConfidence * 100)}%`} tone="neutral" />
              <Chip label={`AP ${state.actionPoints}`} tone="neutral" />
            </div>
          </div>
        </CollapsibleModule>

        <CollapsibleModule
          id="contested-expert"
          title="Expert Metrics"
          tone="contested"
          isOpen={sections.expert}
          onToggle={() => toggle('expert')}
          summary="Raw telemetry fallback"
        >
          <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-4 space-y-2 text-xs font-mono">
            <div>
              Enemy infantry range: {state.contestedPlanet.enemy.infantry.min}-{state.contestedPlanet.enemy.infantry.max}
            </div>
            <div>
              Enemy walkers range: {state.contestedPlanet.enemy.walkers.min}-{state.contestedPlanet.enemy.walkers.max}
            </div>
            <div>
              Enemy support range: {state.contestedPlanet.enemy.support.min}-{state.contestedPlanet.enemy.support.max}
            </div>
            <div>Fortification: {state.contestedPlanet.enemy.fortification.toFixed(2)}</div>
            <div>Reinforcement rate: {state.contestedPlanet.enemy.reinforcementRate.toFixed(2)}</div>
            <div>Readiness: {Math.round(state.taskForce.readiness * 100)}%</div>
            <div>Cohesion: {Math.round(state.taskForce.cohesion * 100)}%</div>
            {state.operation && (
              <div>
                Active operation: {state.operation.currentPhase} day {state.operation.dayInOperation}/{state.operation.estimatedTotalDays}
              </div>
            )}
          </div>
        </CollapsibleModule>
      </div>
    </div>
  );
}
