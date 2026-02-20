import type { CampaignView } from '../../api/types';

interface CampaignNextActionPanelProps {
  campaignView: CampaignView;
  onPrimaryAction: () => void;
  onAutoAdvance: () => void;
  onStopAutoAdvance: () => void;
  autoRunning: boolean;
  autoStatus: string;
}

export function CampaignNextActionPanel({
  campaignView,
  onPrimaryAction,
  onAutoAdvance,
  onStopAutoAdvance,
  autoRunning,
  autoStatus,
}: CampaignNextActionPanelProps) {
  const action = campaignView.nextAction;
  const blocked = Boolean(action.blockingReason);
  const showAutoControls =
    campaignView.stage === 'active_operation' &&
    action.id === 'advance_day';

  return (
    <section className="campaign-card campaign-next-action" aria-label="Next action">
      <h3 className="campaign-title">Next Best Action</h3>
      <div className="campaign-next-copy">{action.reason}</div>
      {action.blockingReason && (
        <div className="campaign-blocker" role="status">
          {action.blockingReason}
        </div>
      )}
      <button
        type="button"
        onClick={onPrimaryAction}
        className="campaign-primary-btn"
      >
        {action.label}
      </button>

      {showAutoControls && (
        <div className="campaign-auto-controls">
          <button
            type="button"
            className="campaign-secondary-btn"
            onClick={autoRunning ? onStopAutoAdvance : onAutoAdvance}
            aria-live="polite"
          >
            {autoRunning ? 'Stop Guided Auto-Advance' : 'Run Guided Auto-Advance'}
          </button>
          <div className="campaign-auto-status">{autoStatus}</div>
        </div>
      )}

      {!showAutoControls && blocked && (
        <div className="campaign-auto-status">Resolve blockers to unlock progression.</div>
      )}
    </section>
  );
}
