import { useEffect, useMemo, useState } from 'react';
import type { ApiResponse, CatalogResponse, GameStateResponse } from '../../api/types';
import {
  postAckAar,
  postAckPhase,
  postAdvanceDay,
  postStartOperation,
  postSubmitPhaseDecisions,
} from '../../api/client';
import { useGuidedAutoAdvance } from '../../hooks/useGuidedAutoAdvance';
import { AarNarrativePanel } from './AarNarrativePanel';
import { CampaignChroniclePanel } from './CampaignChroniclePanel';
import { CampaignNextActionPanel } from './CampaignNextActionPanel';
import { CampaignReadinessPanel } from './CampaignReadinessPanel';
import { CampaignStageRail } from './CampaignStageRail';
import { OperationPlannerPanel } from './OperationPlannerPanel';
import { OperationTimelinePanel } from './OperationTimelinePanel';
import { PhaseDecisionPanel } from './PhaseDecisionPanel';
import { PhaseReportPanel } from './PhaseReportPanel';
import { formatPct } from './helpers';

interface CampaignCommandSurfaceProps {
  state: GameStateResponse;
  catalog: CatalogResponse | null;
  onActionResult: (resp: ApiResponse) => void;
  onClose: () => void;
}

export function CampaignCommandSurface({
  state,
  catalog,
  onActionResult,
  onClose,
}: CampaignCommandSurfaceProps) {
  const campaignView = state.campaignView;
  const availableTargets = catalog?.operationTargets ?? [];
  const availableOpTypes = catalog?.operationTypes ?? [];
  const [target, setTarget] = useState(availableTargets[0]?.id ?? 'foundry');
  const [opType, setOpType] = useState('campaign');
  const [phase1, setPhase1] = useState({ axis: '', fire: '' });
  const [phase2, setPhase2] = useState({ posture: '', risk: '' });
  const [phase3, setPhase3] = useState({ focus: '', endState: '' });

  const autoAdvance = useGuidedAutoAdvance(state, onActionResult);

  useEffect(() => {
    if (!availableTargets.find(item => item.id === target) && availableTargets[0]) {
      setTarget(availableTargets[0].id);
    }
  }, [availableTargets, target]);

  useEffect(() => {
    const preferredType = availableOpTypes.find(item => item.id === 'campaign');
    if (preferredType && opType !== preferredType.id) {
      setOpType(preferredType.id);
      return;
    }
    if (!availableOpTypes.find(item => item.id === opType) && availableOpTypes[0]) {
      setOpType(availableOpTypes[0].id);
    }
  }, [availableOpTypes, opType]);

  const selectedOpType = useMemo(
    () => availableOpTypes.find(item => item.id === opType),
    [availableOpTypes, opType]
  );

  const launchOperation = async () => {
    const resp = await postStartOperation({ target, opType });
    onActionResult(resp);
  };

  const submitPhaseDecisions = async () => {
    if (!state.operation) return;
    if (state.operation.currentPhase === 'contact_shaping') {
      const resp = await postSubmitPhaseDecisions({ axis: phase1.axis, fire: phase1.fire });
      onActionResult(resp);
      return;
    }
    if (state.operation.currentPhase === 'engagement') {
      const resp = await postSubmitPhaseDecisions({ posture: phase2.posture, risk: phase2.risk });
      onActionResult(resp);
      return;
    }
    const resp = await postSubmitPhaseDecisions({ focus: phase3.focus, endState: phase3.endState });
    onActionResult(resp);
  };

  const executePrimaryAction = async () => {
    const action = campaignView.nextAction.id;
    if (action === 'start_operation') {
      await launchOperation();
      return;
    }
    if (action === 'submit_phase_decisions') {
      await submitPhaseDecisions();
      return;
    }
    if (action === 'advance_day') {
      const resp = await postAdvanceDay();
      onActionResult(resp);
      return;
    }
    if (action === 'ack_phase_report') {
      const resp = await postAckPhase();
      onActionResult(resp);
      return;
    }
    if (action === 'ack_aar') {
      const resp = await postAckAar();
      onActionResult(resp);
    }
  };

  return (
    <section className="campaign-shell" aria-label="Campaign command surface">
      <div className="campaign-header campaign-card">
        <div>
          <h2 className="campaign-title">Campaign Command Surface</h2>
          <div className="campaign-subtle">
            Stage {campaignView.stage.replace(/_/g, ' ')} | Objectives {campaignView.objectiveProgress.secured}/
            {campaignView.objectiveProgress.total} secured
          </div>
        </div>
        <button type="button" className="campaign-secondary-btn" onClick={onClose}>
          Return to Strategic Map
        </button>
      </div>

      <div className="campaign-grid">
        <CampaignStageRail stage={campaignView.stage} />

        <div className="campaign-main">
          <CampaignNextActionPanel
            campaignView={campaignView}
            onPrimaryAction={executePrimaryAction}
            onAutoAdvance={() => autoAdvance.run(20)}
            onStopAutoAdvance={autoAdvance.stop}
            autoRunning={autoAdvance.running}
            autoStatus={autoAdvance.message}
          />

          {campaignView.stage === 'preparation' && (
            <OperationPlannerPanel
              catalog={catalog}
              campaignView={campaignView}
              target={target}
              opType={opType}
              onTargetChange={setTarget}
              onTypeChange={setOpType}
              onLaunch={launchOperation}
            />
          )}

          {campaignView.stage === 'active_operation' && state.operation && state.operation.awaitingDecision && (
            <PhaseDecisionPanel
              operation={state.operation}
              catalog={catalog}
              phase1={phase1}
              phase2={phase2}
              phase3={phase3}
              onChangePhase1={setPhase1}
              onChangePhase2={setPhase2}
              onChangePhase3={setPhase3}
              onSubmit={submitPhaseDecisions}
            />
          )}

          {campaignView.stage === 'phase_report' && state.operation?.pendingPhaseRecord && (
            <PhaseReportPanel
              report={state.operation.pendingPhaseRecord}
              onAcknowledge={async () => {
                const resp = await postAckPhase();
                onActionResult(resp);
              }}
            />
          )}

          {campaignView.stage === 'aar_review' && state.lastAar && (
            <AarNarrativePanel
              report={state.lastAar}
              onAcknowledge={async () => {
                const resp = await postAckAar();
                onActionResult(resp);
              }}
            />
          )}

          {campaignView.stage === 'campaign_complete' && (
            <section className="campaign-card">
              <h3 className="campaign-title">Campaign Complete</h3>
              <div className="campaign-subtle">
                All strategic objectives are secured. Preserve readiness and monitor logistics pressure for hold phase.
              </div>
            </section>
          )}

          {state.operation && <OperationTimelinePanel operation={state.operation} />}
        </div>

        <div className="campaign-side">
          <CampaignReadinessPanel campaignView={campaignView} />
          <section className="campaign-card" aria-label="Enemy intelligence">
            <h3 className="campaign-title">Intel Brief</h3>
            <div className="campaign-kpi-grid">
              <div>
                Infantry {state.contestedPlanet.enemy.infantry.min}-{state.contestedPlanet.enemy.infantry.max}
              </div>
              <div>
                Walkers {state.contestedPlanet.enemy.walkers.min}-{state.contestedPlanet.enemy.walkers.max}
              </div>
              <div>
                Support {state.contestedPlanet.enemy.support.min}-{state.contestedPlanet.enemy.support.max}
              </div>
              <div>Confidence {formatPct(state.contestedPlanet.enemy.intelConfidence, 0)}</div>
              <div>Fortification {state.contestedPlanet.enemy.fortification.toFixed(2)}</div>
              <div>Reinforcement {state.contestedPlanet.enemy.reinforcementRate.toFixed(2)}</div>
            </div>
            {selectedOpType?.description && <div className="campaign-subtle">{selectedOpType.description}</div>}
          </section>
          <CampaignChroniclePanel campaignLog={campaignView.campaignLog} />
        </div>
      </div>
    </section>
  );
}
