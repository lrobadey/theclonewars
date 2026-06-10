import { useEffect, useState } from 'react';
import type { ApiResponse, CatalogOption, CatalogResponse, GameStateResponse } from '../../api/types';
import { postAckAar, postAckPhase, postStartOperation, postSubmitPhaseDecisions } from '../../api/client';
import { Chip } from './ui/Chip';
import { InlineProgress } from './ui/InlineProgress';
import { KpiTile } from './ui/KpiTile';
import { SectionHeader } from './ui/SectionHeader';
import { GlassCard } from '../ui/GlassCard';

interface ContestedSystemBarProps {
  state: GameStateResponse;
  catalog: CatalogResponse | null;
  onActionResult: (resp: ApiResponse) => void;
}

type Phase1Form = { axis: string; fire: string };
type Phase2Form = { posture: string; risk: string };
type Phase3Form = { focus: string; endState: string };

function formatPct(value: number, digits = 0) {
  return `${(value * 100).toFixed(digits)}%`;
}

function phaseLabel(phase: string) {
  if (phase === 'contact_shaping') return 'Contact & Shaping';
  if (phase === 'engagement') return 'Main Engagement';
  if (phase === 'exploit_consolidate') return 'Exploit & Consolidate';
  if (phase === 'complete') return 'Complete';
  return phase.replace(/_/g, ' ');
}

function objectiveTone(status: string): 'good' | 'warn' | 'danger' {
  if (status === 'secured') return 'good';
  if (status === 'contested') return 'warn';
  return 'danger';
}

function optionLabel(option: CatalogOption | undefined, fallback: string) {
  return option?.label ?? fallback;
}

function optionEnabled(option: CatalogOption | undefined) {
  return option?.availability?.enabled ?? true;
}

export function ContestedSystemBar({ state, catalog, onActionResult }: ContestedSystemBarProps) {
  const [target, setTarget] = useState('foundry');
  const [phase1, setPhase1] = useState<Phase1Form>({ axis: '', fire: '' });
  const [phase2, setPhase2] = useState<Phase2Form>({ posture: '', risk: '' });
  const [phase3, setPhase3] = useState<Phase3Form>({ focus: '', endState: '' });

  const targets = catalog?.operationTargets ?? [];
  const phase1Options = catalog?.decisions.phase1 ?? { approachAxis: [], fireSupportPrep: [] };
  const phase2Options = catalog?.decisions.phase2 ?? { engagementPosture: [], riskTolerance: [] };
  const phase3Options = catalog?.decisions.phase3 ?? { exploitVsSecure: [], endState: [] };

  useEffect(() => {
    if (targets.length > 0 && !targets.some(option => option.id === target)) {
      setTarget(targets[0].id);
    }
  }, [target, targets]);

  useEffect(() => {
    if (!phase1.axis && phase1Options.approachAxis.length > 0) {
      setPhase1(prev => ({ ...prev, axis: phase1Options.approachAxis[0].id }));
    }
    if (!phase1.fire && phase1Options.fireSupportPrep.length > 0) {
      setPhase1(prev => ({ ...prev, fire: phase1Options.fireSupportPrep[0].id }));
    }
  }, [phase1.axis, phase1.fire, phase1Options.approachAxis, phase1Options.fireSupportPrep]);

  useEffect(() => {
    if (!phase2.posture && phase2Options.engagementPosture.length > 0) {
      setPhase2(prev => ({ ...prev, posture: phase2Options.engagementPosture[0].id }));
    }
    if (!phase2.risk && phase2Options.riskTolerance.length > 0) {
      setPhase2(prev => ({ ...prev, risk: phase2Options.riskTolerance[0].id }));
    }
  }, [phase2.posture, phase2.risk, phase2Options.engagementPosture, phase2Options.riskTolerance]);

  useEffect(() => {
    if (!phase3.focus && phase3Options.exploitVsSecure.length > 0) {
      setPhase3(prev => ({ ...prev, focus: phase3Options.exploitVsSecure[0].id }));
    }
    if (!phase3.endState && phase3Options.endState.length > 0) {
      setPhase3(prev => ({ ...prev, endState: phase3Options.endState[0].id }));
    }
  }, [phase3.endState, phase3.focus, phase3Options.endState, phase3Options.exploitVsSecure]);

  const objectiveProgress = state.contestedPlanet.objectives;
  const securedCount = objectiveProgress.filter(objective => objective.status === 'secured').length;
  const activeOperation = state.operation;
  const pendingPhaseRecord = state.operation?.pendingPhaseRecord ?? null;
  const topFactors = state.lastAar?.topFactors ?? [];
  const aarTone =
    !state.lastAar || state.lastAar.outcome === 'FAILED'
      ? 'danger'
      : state.lastAar.outcome === 'WITHDREW'
        ? 'warn'
        : 'good';

  const launchOperation = async () => {
    const resp = await postStartOperation({ target, opType: 'campaign' });
    onActionResult(resp);
  };

  const submitPhaseDecisions = async () => {
    if (!activeOperation) return;
    if (activeOperation.currentPhase === 'contact_shaping') {
      const resp = await postSubmitPhaseDecisions({ axis: phase1.axis, fire: phase1.fire });
      onActionResult(resp);
      return;
    }
    if (activeOperation.currentPhase === 'engagement') {
      const resp = await postSubmitPhaseDecisions({ posture: phase2.posture, risk: phase2.risk });
      onActionResult(resp);
      return;
    }
    const resp = await postSubmitPhaseDecisions({ focus: phase3.focus, endState: phase3.endState });
    onActionResult(resp);
  };

  const acknowledgePhase = async () => {
    const resp = await postAckPhase();
    onActionResult(resp);
  };

  const acknowledgeAar = async () => {
    const resp = await postAckAar();
    onActionResult(resp);
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-5">
        <KpiTile label="Objectives" value={`${securedCount}/${objectiveProgress.length}`} tone="contested" />
        <KpiTile label="Control" value={formatPct(state.contestedPlanet.control, 0)} tone="contested" />
        <KpiTile label="Intel" value={formatPct(state.contestedPlanet.enemy.intelConfidence, 0)} tone="neutral" />
        <KpiTile label="Readiness" value={formatPct(state.taskForce.readiness, 0)} tone="neutral" />
        <KpiTile label="Cohesion" value={formatPct(state.taskForce.cohesion, 0)} tone="neutral" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_0.95fr]">
        <GlassCard tone="contested" elevation="low" className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeader title="Planet Status" tone="contested" />
            <Chip label={`AP ${state.actionPoints}`} tone="neutral" />
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {objectiveProgress.map(objective => (
              <GlassCard key={objective.id} tone="contested" elevation="low" className="p-3">
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                  {objective.label}
                </div>
                <div className="mt-2 text-sm text-text-primary">{objective.status}</div>
                <div className="mt-2">
                  <Chip label={objective.status} tone={objectiveTone(objective.status)} />
                </div>
              </GlassCard>
            ))}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <KpiTile label="Fortification" value={state.contestedPlanet.enemy.fortification.toFixed(2)} tone="contested" />
            <KpiTile label="Reinforcement" value={state.contestedPlanet.enemy.reinforcementRate.toFixed(2)} tone="contested" />
            <KpiTile label="Confidence" value={formatPct(state.contestedPlanet.enemy.intelConfidence, 0)} tone="contested" />
          </div>
        </GlassCard>

        <GlassCard tone="contested" elevation="low" className="p-4">
          <SectionHeader title="Enemy Intel" tone="contested" />
          <div className="mt-4 grid gap-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <KpiTile
                label="Infantry"
                value={`${state.contestedPlanet.enemy.infantry.min}-${state.contestedPlanet.enemy.infantry.max}`}
                tone="neutral"
              />
              <KpiTile
                label="Walkers"
                value={`${state.contestedPlanet.enemy.walkers.min}-${state.contestedPlanet.enemy.walkers.max}`}
                tone="neutral"
              />
              <KpiTile
                label="Support"
                value={`${state.contestedPlanet.enemy.support.min}-${state.contestedPlanet.enemy.support.max}`}
                tone="neutral"
              />
            </div>
            <div className="space-y-2 rounded border border-white/10 bg-space/40 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Confidence</div>
                <Chip label={formatPct(state.contestedPlanet.enemy.intelConfidence, 0)} tone="neutral" />
              </div>
              <InlineProgress value={state.contestedPlanet.enemy.intelConfidence} tone="contested" />
              <div className="text-sm text-text-secondary">
                Lower confidence broadens the estimate and increases operation variance.
              </div>
            </div>
          </div>
        </GlassCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <GlassCard tone="contested" elevation="low" className="p-4">
          <SectionHeader title="Task Force" tone="contested" />
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <KpiTile label="Infantry" value={state.taskForce.composition.infantry.toLocaleString()} tone="neutral" />
            <KpiTile label="Walkers" value={state.taskForce.composition.walkers.toLocaleString()} tone="neutral" />
            <KpiTile label="Support" value={state.taskForce.composition.support.toLocaleString()} tone="neutral" />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <KpiTile label="Ammo" value={state.taskForce.supplies.ammo.toLocaleString()} tone="contested" />
            <KpiTile label="Fuel" value={state.taskForce.supplies.fuel.toLocaleString()} tone="contested" />
            <KpiTile label="Med+Spares" value={state.taskForce.supplies.medSpares.toLocaleString()} tone="contested" />
          </div>
        </GlassCard>

        <GlassCard tone="contested" elevation="low" className="p-4">
          <SectionHeader title="Operation Control" tone="contested" />

          {!activeOperation && !state.lastAar && (
            <div className="mt-4 space-y-3">
              <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
                <label className="space-y-1">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">Target</div>
                  <select
                    value={target}
                    onChange={event => setTarget(event.target.value)}
                    className="w-full rounded border border-white/10 bg-space/60 px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-contested/60"
                  >
                    {targets.length > 0 ? (
                      targets.map(option => (
                        <option key={option.id} value={option.id} disabled={!optionEnabled(option)}>
                          {optionLabel(option, option.id)}
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="foundry">Droid Foundry</option>
                        <option value="comms">Communications Array</option>
                        <option value="power">Power Plant</option>
                      </>
                    )}
                  </select>
                </label>

                <button
                  type="button"
                  onClick={launchOperation}
                  disabled={state.actionPoints < 1 || !target}
                  className="btn-action rounded border border-contested/30 px-4 py-2 text-[10px] uppercase tracking-[0.22em] text-contested"
                >
                  Launch Campaign
                </button>
              </div>
              <div className="text-sm text-text-secondary">
                Start one campaign operation at a time. Phase decisions appear here after launch.
              </div>
            </div>
          )}

          {activeOperation && (
            <div className="mt-4 space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <KpiTile label="Phase" value={phaseLabel(activeOperation.currentPhase)} tone="contested" />
                <KpiTile label="Day in Op" value={activeOperation.dayInOperation} tone="neutral" />
                <KpiTile label="ETA" value={`${activeOperation.estimatedTotalDays}D`} tone="neutral" />
                <KpiTile label="Decision" value={activeOperation.awaitingDecision ? 'Required' : 'Clear'} tone="neutral" />
              </div>

              {activeOperation.awaitingDecision && (
                <div className="space-y-3 rounded border border-white/10 bg-space/40 p-3">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                    {phaseLabel(activeOperation.currentPhase)} decisions
                  </div>

                  {activeOperation.currentPhase === 'contact_shaping' && (
                    <div className="grid gap-3 md:grid-cols-2">
                      <DecisionSelect
                        label="Approach Axis"
                        value={phase1.axis}
                        onChange={value => setPhase1(prev => ({ ...prev, axis: value }))}
                        options={phase1Options.approachAxis}
                      />
                      <DecisionSelect
                        label="Fire Support"
                        value={phase1.fire}
                        onChange={value => setPhase1(prev => ({ ...prev, fire: value }))}
                        options={phase1Options.fireSupportPrep}
                      />
                    </div>
                  )}

                  {activeOperation.currentPhase === 'engagement' && (
                    <div className="grid gap-3 md:grid-cols-2">
                      <DecisionSelect
                        label="Engagement Posture"
                        value={phase2.posture}
                        onChange={value => setPhase2(prev => ({ ...prev, posture: value }))}
                        options={phase2Options.engagementPosture}
                      />
                      <DecisionSelect
                        label="Risk Tolerance"
                        value={phase2.risk}
                        onChange={value => setPhase2(prev => ({ ...prev, risk: value }))}
                        options={phase2Options.riskTolerance}
                      />
                    </div>
                  )}

                  {activeOperation.currentPhase === 'exploit_consolidate' && (
                    <div className="grid gap-3 md:grid-cols-2">
                      <DecisionSelect
                        label="Exploit vs Secure"
                        value={phase3.focus}
                        onChange={value => setPhase3(prev => ({ ...prev, focus: value }))}
                        options={phase3Options.exploitVsSecure}
                      />
                      <DecisionSelect
                        label="End State"
                        value={phase3.endState}
                        onChange={value => setPhase3(prev => ({ ...prev, endState: value }))}
                        options={phase3Options.endState}
                      />
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={submitPhaseDecisions}
                    disabled={
                      (activeOperation.currentPhase === 'contact_shaping' && (!phase1.axis || !phase1.fire)) ||
                      (activeOperation.currentPhase === 'engagement' && (!phase2.posture || !phase2.risk)) ||
                      (activeOperation.currentPhase === 'exploit_consolidate' && (!phase3.focus || !phase3.endState))
                    }
                    className="btn-action rounded border border-contested/30 px-4 py-2 text-[10px] uppercase tracking-[0.22em] text-contested"
                  >
                    Submit Phase Orders
                  </button>
                </div>
              )}

              {pendingPhaseRecord && (
                <div className="space-y-3 rounded border border-white/10 bg-space/40 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                      Phase Report
                    </div>
                    <Chip label={phaseLabel(pendingPhaseRecord.phase)} tone="neutral" />
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    <KpiTile label="Progress" value={pendingPhaseRecord.summary.progressDelta.toFixed(3)} tone="contested" />
                    <KpiTile label="Losses" value={pendingPhaseRecord.summary.losses} tone="contested" />
                    <KpiTile label="Enemy Losses" value={pendingPhaseRecord.summary.enemyLosses} tone="contested" />
                  </div>
                  <InlineProgress value={Math.max(0, Math.min(1, pendingPhaseRecord.summary.progressDelta))} tone="contested" />
                  <div className="flex flex-wrap gap-3 text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">
                    <span>Ammo {pendingPhaseRecord.summary.suppliesSpent.ammo}</span>
                    <span>Fuel {pendingPhaseRecord.summary.suppliesSpent.fuel}</span>
                    <span>Med {pendingPhaseRecord.summary.suppliesSpent.medSpares}</span>
                    <span>Readiness {pendingPhaseRecord.summary.readinessDelta.toFixed(3)}</span>
                    <span>Cohesion {pendingPhaseRecord.summary.cohesionDelta.toFixed(3)}</span>
                  </div>
                  <button
                    type="button"
                    onClick={acknowledgePhase}
                    className="btn-action rounded border border-contested/30 px-4 py-2 text-[10px] uppercase tracking-[0.22em] text-contested"
                  >
                    Acknowledge Phase Report
                  </button>
                </div>
              )}

              {activeOperation && !activeOperation.awaitingDecision && !pendingPhaseRecord && !state.lastAar && (
                <div className="rounded border border-white/10 bg-space/40 p-3 text-sm text-text-secondary">
                  Advance the day from the panel header to continue the operation.
                </div>
              )}
            </div>
          )}

          {state.lastAar && (
            <div className="mt-4 space-y-3 rounded border border-white/10 bg-space/40 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                  After-Action Report
                </div>
                <Chip label={state.lastAar.outcome} tone={aarTone} />
              </div>
              <div className="grid gap-3 md:grid-cols-4">
                <KpiTile label="Days" value={state.lastAar.days} tone="contested" />
                <KpiTile label="Losses" value={state.lastAar.losses} tone="contested" />
                <KpiTile label="Enemy Losses" value={state.lastAar.enemyLosses} tone="contested" />
                <KpiTile label="Remaining Ammo" value={state.lastAar.remainingSupplies.ammo} tone="contested" />
              </div>
              <div className="grid gap-2 md:grid-cols-3">
                <KpiTile label="Fuel" value={state.lastAar.remainingSupplies.fuel} tone="contested" />
                <KpiTile label="Med+Spares" value={state.lastAar.remainingSupplies.medSpares} tone="contested" />
                <KpiTile label="Factors" value={topFactors.length} tone="contested" />
              </div>
              <div className="space-y-2">
                {topFactors.slice(0, 4).map(factor => (
                  <div key={factor.name} className="rounded border border-white/10 bg-space/60 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm text-text-primary">{factor.name}</div>
                      <Chip label={`${factor.value.toFixed(2)} ${factor.delta}`} tone="neutral" />
                    </div>
                    <div className="mt-1 text-xs text-text-secondary">{factor.why}</div>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={acknowledgeAar}
                className="btn-action rounded border border-contested/30 px-4 py-2 text-[10px] uppercase tracking-[0.22em] text-contested"
              >
                Close AAR
              </button>
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}

interface DecisionSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: CatalogOption[];
}

function DecisionSelect({ label, value, onChange, options }: DecisionSelectProps) {
  return (
    <label className="space-y-1">
      <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">{label}</div>
      <select
        value={value}
        onChange={event => onChange(event.target.value)}
        className="w-full rounded border border-white/10 bg-space/60 px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-contested/60"
      >
        {options.length > 0 ? (
          options.map(option => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))
        ) : (
          <option value="">No options available</option>
        )}
      </select>
    </label>
  );
}
