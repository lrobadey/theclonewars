import { useMemo, useState } from 'react';
import type { ApiResponse, GameStateResponse } from '../../api/types';
import {
  postAckAar,
  postAckPhase,
  postRaidResolve,
  postRaidTick,
  postStartOperation,
  postSubmitPhaseDecisions,
} from '../../api/client';
import { Chip } from './ui/Chip';
import { InlineProgress } from './ui/InlineProgress';
import { KpiTile } from './ui/KpiTile';
import { SectionHeader } from './ui/SectionHeader';

interface ContestedSystemBarProps {
  state: GameStateResponse;
  onActionResult: (resp: ApiResponse) => void;
}

type OperationTarget = 'Droid Foundry' | 'Communications Array' | 'Power Plant';
type OperationType = 'campaign' | 'siege' | 'raid';

const OBJECTIVE_LABELS: Record<string, string> = {
  foundry: 'Foundry',
  comms: 'Comms',
  power: 'Power',
};

export function ContestedSystemBar({ state, onActionResult }: ContestedSystemBarProps) {
  const [target, setTarget] = useState<OperationTarget>('Droid Foundry');
  const [opType, setOpType] = useState<OperationType>('campaign');

  const [phase1, setPhase1] = useState({ axis: '', fire: '' });
  const [phase2, setPhase2] = useState({ posture: '', risk: '' });
  const [phase3, setPhase3] = useState({ focus: '', endState: '' });

  const controlPct = Math.round(state.contestedPlanet.control * 100);

  const controlTone = controlPct < 30 ? 'contested' : controlPct < 60 ? 'deep' : 'core';

  const submitStart = async () => {
    const resp = await postStartOperation({ target, opType });
    onActionResult(resp);
  };

  const submitPhase = async () => {
    if (!state.operation) return;
    const phase = state.operation.currentPhase;
    if (phase === 'contact_shaping') {
      const resp = await postSubmitPhaseDecisions({ axis: phase1.axis, fire: phase1.fire });
      onActionResult(resp);
    } else if (phase === 'engagement') {
      const resp = await postSubmitPhaseDecisions({ posture: phase2.posture, risk: phase2.risk });
      onActionResult(resp);
    } else {
      const resp = await postSubmitPhaseDecisions({ focus: phase3.focus, endState: phase3.endState });
      onActionResult(resp);
    }
  };

  const handleAckPhase = async () => {
    const resp = await postAckPhase();
    onActionResult(resp);
  };

  const handleRaidTick = async () => {
    const resp = await postRaidTick();
    onActionResult(resp);
  };

  const handleRaidResolve = async () => {
    const resp = await postRaidResolve();
    onActionResult(resp);
  };

  const handleAckAar = async () => {
    const resp = await postAckAar();
    onActionResult(resp);
  };

  const objectives = useMemo(() => {
    return state.contestedPlanet.objectives.map(obj => ({
      ...obj,
      label: OBJECTIVE_LABELS[obj.id] ?? obj.label,
    }));
  }, [state.contestedPlanet.objectives]);

  const awaitingDecision = state.operation?.awaitingDecision ?? false;
  const pendingPhase = state.operation?.pendingPhaseRecord;
  const phaseOrder = ['contact_shaping', 'engagement', 'exploit_consolidate', 'complete'];
  const currentPhaseIndex = state.operation ? phaseOrder.indexOf(state.operation.currentPhase) : -1;

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <SectionHeader title="Planet Control" tone="contested" />
          <div className="rounded border border-white/10 bg-space/40 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Control</div>
              <div className="text-xl font-mono font-bold">{controlPct}%</div>
            </div>
            <InlineProgress value={controlPct / 100} tone={controlTone} />
            <div className="grid grid-cols-2 gap-3">
              <KpiTile label="Fortification" value={state.contestedPlanet.enemy.fortification.toFixed(2)} tone="neutral" />
              <KpiTile label="Reinforcement" value={state.contestedPlanet.enemy.reinforcementRate.toFixed(2)} tone="neutral" />
              <KpiTile label="Enemy Cohesion" value={`${Math.round(state.contestedPlanet.enemy.cohesion * 100)}%`} tone="neutral" />
              <KpiTile label="Intel Confidence" value={`${Math.round(state.contestedPlanet.enemy.intelConfidence * 100)}%`} tone="neutral" />
            </div>
          </div>

          <SectionHeader title="Objectives" tone="contested" />
          <div className="rounded border border-white/10 bg-space/40 p-4 space-y-2">
            {objectives.map(obj => (
              <div key={obj.id} className="flex items-center justify-between text-sm">
                <div className="font-mono text-text-primary uppercase tracking-[0.12em]">{obj.label}</div>
                <Chip
                  label={obj.status.toUpperCase()}
                  tone={obj.status === 'secured' ? 'good' : obj.status === 'contested' ? 'warn' : 'danger'}
                />
              </div>
            ))}
          </div>

          <SectionHeader title="Enemy Intel" tone="contested" />
          <div className="rounded border border-white/10 bg-space/40 p-4 space-y-3">
            {(['infantry', 'walkers', 'support'] as const).map(key => (
              <div key={key} className="flex items-center justify-between text-sm font-mono">
                <span className="uppercase">{key}</span>
                <span>
                  {state.contestedPlanet.enemy[key].min}–{state.contestedPlanet.enemy[key].max} (
                  {state.contestedPlanet.enemy[key].actual})
                </span>
              </div>
            ))}
            <div className="space-y-2">
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                Confidence
              </div>
              <div className="grid grid-cols-10 gap-1">
                {Array.from({ length: 10 }).map((_, idx) => {
                  const lit = idx < Math.round(state.contestedPlanet.enemy.intelConfidence * 10);
                  return (
                    <div
                      key={idx}
                      className={`h-2 rounded ${lit ? 'bg-contested' : 'bg-white/10'}`}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <SectionHeader title="Task Force" tone="contested" />
          <div className="rounded border border-white/10 bg-space/40 p-4 space-y-3">
            <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
              Location: {state.taskForce.location}
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span>Readiness</span>
                <span>{Math.round(state.taskForce.readiness * 100)}%</span>
              </div>
              <InlineProgress value={state.taskForce.readiness} tone="core" />
              <div className="flex items-center justify-between text-xs font-mono">
                <span>Cohesion</span>
                <span>{Math.round(state.taskForce.cohesion * 100)}%</span>
              </div>
              <InlineProgress value={state.taskForce.cohesion} tone="deep" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <KpiTile label="Ammo" value={state.taskForce.supplies.ammo} tone="neutral" />
              <KpiTile label="Fuel" value={state.taskForce.supplies.fuel} tone="neutral" />
              <KpiTile label="Med+Spares" value={state.taskForce.supplies.medSpares} tone="neutral" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <KpiTile label="Infantry" value={state.taskForce.composition.infantry} tone="neutral" />
              <KpiTile label="Walkers" value={state.taskForce.composition.walkers} tone="neutral" />
              <KpiTile label="Support" value={state.taskForce.composition.support} tone="neutral" />
            </div>
          </div>

          <SectionHeader title="Operations & Raid" tone="contested" />
          <div className="rounded border border-white/10 bg-space/40 p-4 space-y-4">
            {state.raid ? (
              <div className="space-y-3">
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                  Raid Progress {state.raid.tick}/{state.raid.maxTicks}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <KpiTile label="Your Cohesion" value={state.raid.yourCohesion.toFixed(2)} />
                  <KpiTile label="Enemy Cohesion" value={state.raid.enemyCohesion.toFixed(2)} />
                  <KpiTile label="Your Casualties" value={state.raid.yourCasualties} />
                  <KpiTile label="Enemy Casualties" value={state.raid.enemyCasualties} />
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                    Tick Log
                  </div>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {state.raid.tickLog
                      .slice(-10)
                      .reverse()
                      .map((entry, idx) => (
                      <div key={`${entry.tick}-${idx}`} className="text-xs font-mono text-text-secondary">
                        [{entry.tick}] {entry.event} — {entry.beat}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleRaidTick}
                    className="btn-action px-3 py-1 text-[10px] uppercase tracking-[0.2em] border border-contested/40 text-contested"
                  >
                    Advance Tick
                  </button>
                  <button
                    onClick={handleRaidResolve}
                    className="btn-action px-3 py-1 text-[10px] uppercase tracking-[0.2em] border border-contested/40 text-contested"
                  >
                    Resolve Raid
                  </button>
                </div>
              </div>
            ) : !state.operation ? (
              <div className="space-y-3">
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                  Launch Operation
                </div>
                <div className="space-y-2">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                    Target
                  </div>
                  {(['Droid Foundry', 'Communications Array', 'Power Plant'] as OperationTarget[]).map(item => (
                    <label key={item} className="flex items-center gap-2 text-xs font-mono">
                      <input
                        type="radio"
                        checked={target === item}
                        onChange={() => setTarget(item)}
                      />
                      {item}
                    </label>
                  ))}
                </div>
                <div className="space-y-2">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                    Operation Type
                  </div>
                  {(['campaign', 'siege', 'raid'] as OperationType[]).map(item => (
                    <label key={item} className="flex items-center gap-2 text-xs font-mono">
                      <input type="radio" checked={opType === item} onChange={() => setOpType(item)} />
                      {item}
                    </label>
                  ))}
                </div>
                <button
                  onClick={submitStart}
                  className="btn-action px-3 py-2 text-[10px] uppercase tracking-[0.2em] border border-contested/40 text-contested"
                >
                  Launch
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-xs font-mono text-text-secondary uppercase tracking-[0.2em]">
                  Operation Status
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div>Target: {state.operation.target}</div>
                  <div>Type: {state.operation.opType}</div>
                  <div>Phase: {state.operation.currentPhase}</div>
                  <div>Day {state.operation.dayInOperation} / {state.operation.estimatedTotalDays}</div>
                </div>
                <div className="grid grid-cols-4 gap-1 text-[10px] uppercase tracking-[0.2em] text-text-secondary">
                  {['Contact_Shaping', 'Engagement', 'Exploit_Consolidate', 'Complete'].map((step, idx) => (
                    <div
                      key={step}
                      className={`rounded border px-2 py-1 text-center ${
                        idx <= currentPhaseIndex
                          ? 'border-contested text-contested'
                          : 'border-white/10'
                      }`}
                    >
                      {step}
                    </div>
                  ))}
                </div>

                {pendingPhase ? (
                  <div className="rounded border border-contested/30 bg-contested/5 p-3 space-y-2">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                      Phase Report
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                      <div>Progress Δ: {pendingPhase.summary.progressDelta}</div>
                      <div>Losses: {pendingPhase.summary.losses}</div>
                      <div>Ammo: {pendingPhase.summary.suppliesSpent.ammo}</div>
                      <div>Fuel: {pendingPhase.summary.suppliesSpent.fuel}</div>
                      <div>Med: {pendingPhase.summary.suppliesSpent.medSpares}</div>
                      <div>Readiness Δ: {pendingPhase.summary.readinessDelta}</div>
                      <div>Cohesion Δ: {pendingPhase.summary.cohesionDelta}</div>
                    </div>
                    <div className="space-y-1 max-h-32 overflow-y-auto text-xs font-mono text-text-secondary">
                      {pendingPhase.events.map((ev, idx) => (
                        <div key={`${ev.name}-${idx}`}>
                          {ev.name}: {ev.value} ({ev.delta}) — {ev.why}
                        </div>
                      ))}
                    </div>
                    <button
                      onClick={handleAckPhase}
                      className="btn-action px-3 py-2 text-[10px] uppercase tracking-[0.2em] border border-contested/40 text-contested"
                    >
                      Acknowledge Phase Report
                    </button>
                  </div>
                ) : awaitingDecision ? (
                  <div className="space-y-3">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                      Phase Decisions
                    </div>
                    {state.operation.currentPhase === 'contact_shaping' && (
                      <div className="space-y-2">
                        <RadioGroup
                          label="Approach Axis"
                          options={['direct', 'flank', 'dispersed', 'stealth']}
                          value={phase1.axis}
                          onChange={value => setPhase1(prev => ({ ...prev, axis: value }))}
                        />
                        <RadioGroup
                          label="Fire Support Prep"
                          options={['conserve', 'preparatory']}
                          value={phase1.fire}
                          onChange={value => setPhase1(prev => ({ ...prev, fire: value }))}
                        />
                      </div>
                    )}
                    {state.operation.currentPhase === 'engagement' && (
                      <div className="space-y-2">
                        <RadioGroup
                          label="Engagement Posture"
                          options={['shock', 'methodical', 'siege', 'feint']}
                          value={phase2.posture}
                          onChange={value => setPhase2(prev => ({ ...prev, posture: value }))}
                        />
                        <RadioGroup
                          label="Risk Tolerance"
                          options={['low', 'med', 'high']}
                          value={phase2.risk}
                          onChange={value => setPhase2(prev => ({ ...prev, risk: value }))}
                        />
                      </div>
                    )}
                    {state.operation.currentPhase === 'exploit_consolidate' && (
                      <div className="space-y-2">
                        <RadioGroup
                          label="Focus"
                          options={['push', 'secure']}
                          value={phase3.focus}
                          onChange={value => setPhase3(prev => ({ ...prev, focus: value }))}
                        />
                        <RadioGroup
                          label="End State"
                          options={['capture', 'raid', 'destroy', 'withdraw']}
                          value={phase3.endState}
                          onChange={value => setPhase3(prev => ({ ...prev, endState: value }))}
                        />
                      </div>
                    )}
                    <button
                      onClick={submitPhase}
                      disabled={
                        (state.operation.currentPhase === 'contact_shaping' &&
                          (!phase1.axis || !phase1.fire)) ||
                        (state.operation.currentPhase === 'engagement' && (!phase2.posture || !phase2.risk)) ||
                        (state.operation.currentPhase === 'exploit_consolidate' &&
                          (!phase3.focus || !phase3.endState))
                      }
                      className="btn-action px-3 py-2 text-[10px] uppercase tracking-[0.2em] border border-contested/40 text-contested disabled:opacity-40"
                    >
                      Submit Decisions
                    </button>
                  </div>
                ) : (
                  <div className="text-xs font-mono text-text-secondary">
                    Awaiting next day tick. Use Advance Day to proceed.
                  </div>
                )}
              </div>
            )}
          </div>

          {state.lastAar && (
            <div className="rounded border border-white/10 bg-space/40 p-4 space-y-3">
              <SectionHeader title="After Action Report" tone="contested" />
              {state.lastAar.kind === 'operation' ? (
                <div className="space-y-2 text-xs font-mono">
                  <div>Outcome: {state.lastAar.outcome}</div>
                  <div>Target: {state.lastAar.target}</div>
                  <div>Op Type: {state.lastAar.operationType}</div>
                  <div>Days: {state.lastAar.days}</div>
                  <div>Losses: {state.lastAar.losses}</div>
                  <div>
                    Remaining Supplies: A{state.lastAar.remainingSupplies.ammo} / F
                    {state.lastAar.remainingSupplies.fuel} / M
                    {state.lastAar.remainingSupplies.medSpares}
                  </div>
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">
                      Top Factors
                    </div>
                    {state.lastAar.topFactors.map((factor, idx) => (
                      <div key={`${factor.name}-${idx}`}>
                        {factor.name}: {factor.value} ({factor.delta}) — {factor.why}
                      </div>
                    ))}
                  </div>
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">
                      Phases
                    </div>
                    {state.lastAar.phases.map((phase, idx) => (
                      <div key={`${phase.phase}-${idx}`}>
                        {phase.phase} Day {phase.startDay}–{phase.endDay}: Progress {phase.summary.progressDelta}, Losses{' '}
                        {phase.summary.losses}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-2 text-xs font-mono">
                  <div>Outcome: {state.lastAar.outcome}</div>
                  <div>Reason: {state.lastAar.reason}</div>
                  <div>Target: {state.lastAar.target}</div>
                  <div>Ticks: {state.lastAar.ticks}</div>
                  <div>
                    Casualties: Your {state.lastAar.yourCasualties} / Enemy {state.lastAar.enemyCasualties}
                  </div>
                  <div>
                    Supplies Used: A{state.lastAar.suppliesUsed.ammo} / F{state.lastAar.suppliesUsed.fuel} / M
                    {state.lastAar.suppliesUsed.medSpares}
                  </div>
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">
                      Key Moments
                    </div>
                    {state.lastAar.keyMoments.map((moment, idx) => (
                      <div key={`${moment}-${idx}`}>{moment}</div>
                    ))}
                  </div>
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">
                      Top Factors
                    </div>
                    {state.lastAar.topFactors.map((factor, idx) => (
                      <div key={`${factor.name}-${idx}`}>
                        {factor.name}: {factor.value} — {factor.why}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <button
                onClick={handleAckAar}
                className="btn-action px-3 py-2 text-[10px] uppercase tracking-[0.2em] border border-contested/40 text-contested"
              >
                Acknowledge AAR
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RadioGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1">
      <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">{label}</div>
      <div className="grid grid-cols-2 gap-2">
        {options.map(option => (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            className={`px-2 py-1 text-[10px] uppercase tracking-[0.2em] border ${
              value === option ? 'bg-contested text-space border-contested' : 'border-contested/30 text-contested'
            }`}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
