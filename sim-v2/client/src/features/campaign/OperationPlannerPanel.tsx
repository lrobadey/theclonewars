import type { CatalogResponse, CampaignView } from '../../api/types';
import { toneForObjective } from './helpers';

interface OperationPlannerPanelProps {
  catalog: CatalogResponse | null;
  campaignView: CampaignView;
  target: string;
  opType: string;
  onTargetChange: (target: string) => void;
  onTypeChange: (opType: string) => void;
  onLaunch: () => void;
}

export function OperationPlannerPanel({
  catalog,
  campaignView,
  target,
  opType,
  onTargetChange,
  onTypeChange,
  onLaunch,
}: OperationPlannerPanelProps) {
  const targets = catalog?.operationTargets ?? [];
  const opTypes = catalog?.operationTypes ?? [];

  return (
    <section className="campaign-card campaign-planner" aria-label="Operation planner">
      <h3 className="campaign-title">Operation Planner</h3>
      <div className="campaign-objectives">
        {campaignView.objectiveProgress.objectives.map(objective => (
          <div key={objective.id} className="campaign-objective-row">
            <span>{objective.label}</span>
            <span className={`campaign-chip ${toneForObjective(objective.status)}`}>{objective.status}</span>
          </div>
        ))}
      </div>
      <div className="campaign-form-grid">
        <label className="campaign-field">
          <span>Target</span>
          <select value={target} onChange={e => onTargetChange(e.target.value)}>
            {targets.map(item => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="campaign-field">
          <span>Operation Type</span>
          <select value={opType} onChange={e => onTypeChange(e.target.value)}>
            {opTypes.map(item => (
              <option key={item.id} value={item.id} disabled={item.availability?.enabled === false}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {opTypes.find(item => item.id === opType)?.availability?.enabled === false && (
        <div className="campaign-blocker">
          {opTypes.find(item => item.id === opType)?.availability?.reason ?? 'Unavailable'}
        </div>
      )}
      <button type="button" className="campaign-secondary-btn" onClick={onLaunch}>
        Launch Operation
      </button>
    </section>
  );
}
