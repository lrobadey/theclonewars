import type { CampaignView } from '../../api/types';

interface CampaignChroniclePanelProps {
  campaignLog: CampaignView['campaignLog'];
}

export function CampaignChroniclePanel({ campaignLog }: CampaignChroniclePanelProps) {
  return (
    <section className="campaign-card campaign-chronicle" aria-label="Campaign chronicle">
      <h3 className="campaign-title">Campaign Chronicle</h3>
      <div className="campaign-events">
        {campaignLog.length === 0 && <div className="campaign-subtle">No recent events.</div>}
        {campaignLog.map((entry, idx) => (
          <div key={`${entry.day}-${entry.kind}-${idx}`} className="campaign-event-row">
            <span className="campaign-chip neutral">D{entry.day}</span>
            <span className="campaign-chip neutral">{entry.kind}</span>
            <span>{entry.message}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
