import type { AfterActionReport } from '../../api/types';
import { phaseLabel } from './helpers';

interface AarNarrativePanelProps {
  report: AfterActionReport;
  onAcknowledge: () => void;
}

function recommendationFromFactor(name: string, delta: string) {
  const lowered = name.toLowerCase();
  if (lowered.includes('supply') || delta.includes('supply')) {
    return 'Increase front-line supply depth before next launch.';
  }
  if (lowered.includes('intel') || lowered.includes('variance')) {
    return 'Prioritize lower-variance posture and recon-heavy shaping.';
  }
  if (lowered.includes('fort') || lowered.includes('erosion')) {
    return 'Use fortification-erosion choices earlier in the operation.';
  }
  if (lowered.includes('loss')) {
    return 'Reduce casualty exposure with methodical posture and secure exploitation.';
  }
  return 'Adjust phase decisions to amplify positive factors and suppress negative pressure.';
}

export function AarNarrativePanel({ report, onAcknowledge }: AarNarrativePanelProps) {
  return (
    <section className="campaign-card campaign-aar" aria-label="After action report">
      <h3 className="campaign-title">After Action Report</h3>
      <div className="campaign-kpi-grid">
        <div>Outcome {report.outcome}</div>
        <div>Target {report.target}</div>
        <div>Days {report.days}</div>
        <div>Losses {report.losses}</div>
        <div>Enemy losses {report.enemyLosses}</div>
        <div>
          Remaining A/F/M {report.remainingSupplies.ammo}/{report.remainingSupplies.fuel}/{report.remainingSupplies.medSpares}
        </div>
      </div>
      <div className="campaign-events">
        <div className="campaign-field-label">Top Causal Factors</div>
        {report.topFactors.map(factor => (
          <div key={`${factor.name}-${factor.delta}`} className="campaign-event-row">
            <strong>{factor.name}</strong> {factor.value.toFixed(3)} ({factor.delta}) - {factor.why}
          </div>
        ))}
      </div>
      <div className="campaign-events">
        <div className="campaign-field-label">Recommendations</div>
        {report.topFactors.slice(0, 3).map(factor => (
          <div key={`rec-${factor.name}`} className="campaign-event-row">
            {recommendationFromFactor(factor.name, factor.delta)}
          </div>
        ))}
      </div>
      <div className="campaign-events">
        <div className="campaign-field-label">Phase Timeline</div>
        {report.phases.map(phase => (
          <div key={`${phase.phase}-${phase.startDay}`} className="campaign-event-row">
            {phaseLabel(phase.phase)} D{phase.startDay}-{phase.endDay}: progress {phase.summary.progressDelta.toFixed(3)},
            losses {phase.summary.losses}, enemy {phase.summary.enemyLosses}
          </div>
        ))}
      </div>
      <button type="button" className="campaign-primary-btn" onClick={onAcknowledge}>
        Acknowledge AAR
      </button>
    </section>
  );
}
