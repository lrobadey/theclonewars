import type { PhaseRecord } from '../../api/types';
import { phaseLabel } from './helpers';

interface PhaseReportPanelProps {
  report: PhaseRecord;
  onAcknowledge: () => void;
}

export function PhaseReportPanel({ report, onAcknowledge }: PhaseReportPanelProps) {
  return (
    <section className="campaign-card campaign-phase-report" aria-label="Phase report">
      <h3 className="campaign-title">Phase Report: {phaseLabel(report.phase)}</h3>
      <div className="campaign-kpi-grid">
        <div>Progress Δ {report.summary.progressDelta.toFixed(3)}</div>
        <div>Losses {report.summary.losses}</div>
        <div>Enemy losses {report.summary.enemyLosses}</div>
        <div>Ammo spent {report.summary.suppliesSpent.ammo}</div>
        <div>Fuel spent {report.summary.suppliesSpent.fuel}</div>
        <div>Med spent {report.summary.suppliesSpent.medSpares}</div>
      </div>
      <div className="campaign-events">
        {report.events.slice(0, 8).map(event => (
          <div key={`${event.name}-${event.delta}`} className="campaign-event-row">
            <strong>{event.name}</strong> {event.value.toFixed(3)} ({event.delta}) - {event.why}
          </div>
        ))}
      </div>
      <button type="button" className="campaign-primary-btn" onClick={onAcknowledge}>
        Acknowledge Phase Report
      </button>
    </section>
  );
}
