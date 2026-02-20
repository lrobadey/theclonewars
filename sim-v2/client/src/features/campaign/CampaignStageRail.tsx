import type { CampaignView } from '../../api/types';

const STAGES: Array<{ id: CampaignView['stage']; label: string }> = [
  { id: 'preparation', label: 'Prepare' },
  { id: 'active_operation', label: 'Execute' },
  { id: 'phase_report', label: 'Debrief (Phase)' },
  { id: 'aar_review', label: 'Debrief (AAR)' },
  { id: 'campaign_complete', label: 'Adapt / Hold' },
];

interface CampaignStageRailProps {
  stage: CampaignView['stage'];
}

export function CampaignStageRail({ stage }: CampaignStageRailProps) {
  const currentIndex = STAGES.findIndex(item => item.id === stage);
  return (
    <aside className="campaign-card campaign-stage-rail" aria-label="Campaign stage progression">
      <h3 className="campaign-title">Campaign Flow</h3>
      <div className="campaign-stage-list">
        {STAGES.map((item, idx) => {
          const active = idx === currentIndex;
          const complete = idx < currentIndex;
          return (
            <div
              key={item.id}
              className={`campaign-stage-item ${active ? 'active' : ''} ${complete ? 'complete' : ''}`}
              aria-current={active ? 'step' : undefined}
            >
              <span className="campaign-stage-index">{idx + 1}</span>
              <span className="campaign-stage-label">{item.label}</span>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
