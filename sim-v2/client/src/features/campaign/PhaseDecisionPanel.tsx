import type { CatalogOption, CatalogResponse, OperationState } from '../../api/types';
import { formatSigned, impactToChips, phaseLabel } from './helpers';

interface PhaseDecisionPanelProps {
  operation: OperationState;
  catalog: CatalogResponse | null;
  phase1: { axis: string; fire: string };
  phase2: { posture: string; risk: string };
  phase3: { focus: string; endState: string };
  onChangePhase1: (next: { axis: string; fire: string }) => void;
  onChangePhase2: (next: { posture: string; risk: string }) => void;
  onChangePhase3: (next: { focus: string; endState: string }) => void;
  onSubmit: () => void;
}

function fallbackOptions(kind: string): CatalogOption[] {
  if (kind === 'axis') {
    return [
      { id: 'direct', label: 'Direct' },
      { id: 'flank', label: 'Flank' },
      { id: 'dispersed', label: 'Dispersed' },
      { id: 'stealth', label: 'Stealth' },
    ];
  }
  if (kind === 'fire') return [{ id: 'conserve', label: 'Conserve' }, { id: 'preparatory', label: 'Preparatory' }];
  if (kind === 'posture') {
    return [
      { id: 'shock', label: 'Shock' },
      { id: 'methodical', label: 'Methodical' },
      { id: 'siege', label: 'Siege' },
      { id: 'feint', label: 'Feint' },
    ];
  }
  if (kind === 'risk') return [{ id: 'low', label: 'Low' }, { id: 'med', label: 'Med' }, { id: 'high', label: 'High' }];
  if (kind === 'focus') return [{ id: 'push', label: 'Push' }, { id: 'secure', label: 'Secure' }];
  return [
    { id: 'capture', label: 'Capture' },
    { id: 'raid', label: 'Raid' },
    { id: 'destroy', label: 'Destroy' },
    { id: 'withdraw', label: 'Withdraw' },
  ];
}

function OptionGrid({
  label,
  options,
  value,
  onSelect,
}: {
  label: string;
  options: CatalogOption[];
  value: string;
  onSelect: (value: string) => void;
}) {
  return (
    <div className="campaign-option-block">
      <div className="campaign-field-label">{label}</div>
      <div className="campaign-option-grid" role="radiogroup" aria-label={label}>
        {options.map(option => (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={value === option.id}
            className={`campaign-option-card ${value === option.id ? 'selected' : ''}`}
            onClick={() => onSelect(option.id)}
          >
            <div className="campaign-option-title">{option.label}</div>
            {option.description && <div className="campaign-option-description">{option.description}</div>}
            {option.impact && (
              <div className="campaign-impact-row">
                {impactToChips(option).map(chip => (
                  <span key={chip.label} className={`campaign-chip ${chip.tone}`}>{chip.label}</span>
                ))}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export function PhaseDecisionPanel({
  operation,
  catalog,
  phase1,
  phase2,
  phase3,
  onChangePhase1,
  onChangePhase2,
  onChangePhase3,
  onSubmit,
}: PhaseDecisionPanelProps) {
  const phase = operation.currentPhase;
  const p1Axis = catalog?.decisions.phase1.approachAxis ?? fallbackOptions('axis');
  const p1Fire = catalog?.decisions.phase1.fireSupportPrep ?? fallbackOptions('fire');
  const p2Posture = catalog?.decisions.phase2.engagementPosture ?? fallbackOptions('posture');
  const p2Risk = catalog?.decisions.phase2.riskTolerance ?? fallbackOptions('risk');
  const p3Focus = catalog?.decisions.phase3.exploitVsSecure ?? fallbackOptions('focus');
  const p3End = catalog?.decisions.phase3.endState ?? fallbackOptions('end');

  const selectedImpacts: CatalogOption[] = [];
  if (phase === 'contact_shaping') {
    selectedImpacts.push(...p1Axis.filter(option => option.id === phase1.axis));
    selectedImpacts.push(...p1Fire.filter(option => option.id === phase1.fire));
  }
  if (phase === 'engagement') {
    selectedImpacts.push(...p2Posture.filter(option => option.id === phase2.posture));
    selectedImpacts.push(...p2Risk.filter(option => option.id === phase2.risk));
  }
  if (phase === 'exploit_consolidate') {
    selectedImpacts.push(...p3Focus.filter(option => option.id === phase3.focus));
    selectedImpacts.push(...p3End.filter(option => option.id === phase3.endState));
  }
  const impactSummary = selectedImpacts.reduce(
    (acc, option) => {
      acc.progress += option.impact?.progress ?? 0;
      acc.losses += option.impact?.losses ?? 0;
      acc.variance += option.impact?.variance ?? 0;
      acc.supplies += option.impact?.supplies ?? 0;
      acc.fortification += option.impact?.fortification ?? 0;
      return acc;
    },
    { progress: 0, losses: 0, variance: 0, supplies: 0, fortification: 0 }
  );

  const isComplete =
    (phase === 'contact_shaping' && phase1.axis && phase1.fire) ||
    (phase === 'engagement' && phase2.posture && phase2.risk) ||
    (phase === 'exploit_consolidate' && phase3.focus && phase3.endState);

  return (
    <section className="campaign-card campaign-decisions" aria-label="Phase decisions">
      <h3 className="campaign-title">Phase Orders: {phaseLabel(phase)}</h3>
      <div className="campaign-subtle">
        Day {operation.dayInOperation}/{operation.estimatedTotalDays} | Phase day {operation.dayInPhase}
      </div>
      {phase === 'contact_shaping' && (
        <>
          <OptionGrid
            label="Approach Axis"
            options={p1Axis}
            value={phase1.axis}
            onSelect={value => onChangePhase1({ ...phase1, axis: value })}
          />
          <OptionGrid
            label="Fire Support Prep"
            options={p1Fire}
            value={phase1.fire}
            onSelect={value => onChangePhase1({ ...phase1, fire: value })}
          />
        </>
      )}
      {phase === 'engagement' && (
        <>
          <OptionGrid
            label="Engagement Posture"
            options={p2Posture}
            value={phase2.posture}
            onSelect={value => onChangePhase2({ ...phase2, posture: value })}
          />
          <OptionGrid
            label="Risk Tolerance"
            options={p2Risk}
            value={phase2.risk}
            onSelect={value => onChangePhase2({ ...phase2, risk: value })}
          />
        </>
      )}
      {phase === 'exploit_consolidate' && (
        <>
          <OptionGrid
            label="Exploit vs Secure"
            options={p3Focus}
            value={phase3.focus}
            onSelect={value => onChangePhase3({ ...phase3, focus: value })}
          />
          <OptionGrid
            label="End State"
            options={p3End}
            value={phase3.endState}
            onSelect={value => onChangePhase3({ ...phase3, endState: value })}
          />
        </>
      )}
      <div className="campaign-impact-summary" aria-live="polite">
        <div>Projected impact from selected orders</div>
        <div className="campaign-impact-kpis">
          <span>Progress {formatSigned(impactSummary.progress)}</span>
          <span>Losses {formatSigned(impactSummary.losses)}</span>
          <span>Variance {formatSigned(impactSummary.variance)}</span>
          <span>Supply {formatSigned(impactSummary.supplies)}</span>
          <span>Fortification {formatSigned(impactSummary.fortification)}</span>
        </div>
      </div>
      <button
        type="button"
        className="campaign-primary-btn"
        disabled={!isComplete}
        onClick={onSubmit}
      >
        Submit Phase Orders
      </button>
    </section>
  );
}
