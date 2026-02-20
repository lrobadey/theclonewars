import { useMemo, useState } from 'react';
import type { OperationState } from '../../api/types';
import { phaseLabel } from './helpers';

interface OperationTimelinePanelProps {
  operation: OperationState;
}

export function OperationTimelinePanel({ operation }: OperationTimelinePanelProps) {
  const [showExpert, setShowExpert] = useState(false);
  const recentDays = useMemo(() => operation.currentPhaseDays.slice(-6), [operation.currentPhaseDays]);

  return (
    <section className="campaign-card campaign-timeline" aria-label="Operation timeline">
      <h3 className="campaign-title">Operation Timeline</h3>
      <div className="campaign-subtle">
        Current phase: {phaseLabel(operation.currentPhase)} | Day {operation.dayInOperation}/{operation.estimatedTotalDays}
      </div>
      <div className="campaign-phase-strip">
        {['contact_shaping', 'engagement', 'exploit_consolidate', 'complete'].map(item => {
          const active = operation.currentPhase === item;
          const complete = operation.phaseHistory.some(phase => phase.phase === item);
          return (
            <div key={item} className={`campaign-phase-pill ${active ? 'active' : ''} ${complete ? 'complete' : ''}`}>
              {phaseLabel(item)}
            </div>
          );
        })}
      </div>
      <div className="campaign-history">
        {operation.phaseHistory.length === 0 && <div className="campaign-subtle">No completed phases yet.</div>}
        {operation.phaseHistory.map(record => (
          <div key={`${record.phase}-${record.endDay}`} className="campaign-history-row">
            <div className="campaign-history-head">
              <strong>{phaseLabel(record.phase)}</strong>
              <span>Days {record.startDay}-{record.endDay}</span>
            </div>
            <div className="campaign-history-metrics">
              <span>Progress {record.summary.progressDelta.toFixed(3)}</span>
              <span>Losses {record.summary.losses}</span>
              <span>Enemy {record.summary.enemyLosses}</span>
              <span>Readiness {record.summary.readinessDelta.toFixed(3)}</span>
            </div>
          </div>
        ))}
      </div>

      <button
        type="button"
        className="campaign-secondary-btn"
        onClick={() => setShowExpert(prev => !prev)}
      >
        {showExpert ? 'Hide Expert Metrics' : 'Show Expert Metrics'}
      </button>
      {showExpert && (
        <div className="campaign-expert-box">
          {operation.latestBattleDay && (
            <div className="campaign-expert-grid">
              <span>Terrain: {operation.latestBattleDay.terrainId}</span>
              <span>Force Limit: {operation.latestBattleDay.forceLimitBattalions}</span>
              <span>Eng Cap: {operation.latestBattleDay.engagementCapManpower}</span>
              <span>Advantage: {operation.latestBattleDay.yourAdvantage.toFixed(3)}</span>
            </div>
          )}
          {recentDays.map(day => (
            <div key={`${day.dayIndex}-${day.phase}`} className="campaign-expert-row">
              D{day.dayIndex} {phaseLabel(day.phase)} | progress {day.progressDelta.toFixed(3)} | your losses{' '}
              {Object.values(day.yourLosses).reduce((sum, value) => sum + value, 0)} | enemy losses{' '}
              {Object.values(day.enemyLosses).reduce((sum, value) => sum + value, 0)}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
