import type { CampaignView } from '../../api/types';
import { formatPct } from './helpers';

interface CampaignReadinessPanelProps {
  campaignView: CampaignView;
}

function Meter({ label, value }: { label: string; value: number }) {
  return (
    <div className="campaign-meter">
      <div className="campaign-meter-head">
        <span>{label}</span>
        <span>{formatPct(value, 0)}</span>
      </div>
      <div className="campaign-meter-track">
        <div className="campaign-meter-fill" style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
    </div>
  );
}

export function CampaignReadinessPanel({ campaignView }: CampaignReadinessPanelProps) {
  const { readiness, supplyForecast } = campaignView;
  return (
    <section className="campaign-card campaign-readiness" aria-label="Readiness overview">
      <h3 className="campaign-title">Readiness</h3>
      <Meter label="Overall" value={readiness.overallScore} />
      <Meter label="Force" value={readiness.forceScore} />
      <Meter label="Supply" value={readiness.supplyScore} />
      <Meter label="Route" value={readiness.routeScore} />
      <Meter label="Intel" value={readiness.intelScore} />
      <div className="campaign-forecast">
        <div>Ammo: {supplyForecast.ammoDays.toFixed(1)}d</div>
        <div>Fuel: {supplyForecast.fuelDays.toFixed(1)}d</div>
        <div>Med: {supplyForecast.medDays.toFixed(1)}d</div>
        <div className="campaign-bottleneck">Bottleneck: {supplyForecast.bottleneck}</div>
      </div>
    </section>
  );
}
