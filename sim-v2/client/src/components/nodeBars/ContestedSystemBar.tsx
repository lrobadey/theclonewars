import { useEffect, useMemo, useState } from 'react';
import type { ApiResponse, CatalogResponse, GameStateResponse } from '../../api/types';
import {
  postAckAar,
  postAckPhase,
  postStartOperation,
  postSubmitPhaseDecisions,
} from '../../api/client';
import { Chip } from './ui/Chip';
import { InlineProgress } from './ui/InlineProgress';
import { KpiTile } from './ui/KpiTile';
import { SectionHeader } from './ui/SectionHeader';
import { CollapsibleModule } from './ui/CollapsibleModule';

interface ContestedSystemBarProps {
  state: GameStateResponse;
  catalog: CatalogResponse | null;
  onActionResult: (resp: ApiResponse) => void;
}

type OperationTarget = string;
type OperationType = string;

const FALLBACK_TARGETS: { id: OperationTarget; label: string }[] = [
  { id: 'foundry', label: 'Droid Foundry' },
  { id: 'comms', label: 'Communications Array' },
  { id: 'power', label: 'Power Plant' },
];
const FALLBACK_TYPES: { id: OperationType; label: string }[] = [
  { id: 'campaign', label: 'Campaign' },
  { id: 'siege', label: 'Siege' },
  { id: 'raid', label: 'Raid' },
];

export function ContestedSystemBar({ state, catalog, onActionResult }: ContestedSystemBarProps) {
  const targets = catalog?.operationTargets ?? FALLBACK_TARGETS;
  const types = catalog?.operationTypes ?? FALLBACK_TYPES;
  const phase1Approach = catalog?.decisions.phase1.approachAxis ?? [
    { id: 'direct', label: 'Direct' },
    { id: 'flank', label: 'Flank' },
    { id: 'dispersed', label: 'Dispersed' },
    { id: 'stealth', label: 'Stealth' },
  ];
  const phase1Fire = catalog?.decisions.phase1.fireSupportPrep ?? [
    { id: 'conserve', label: 'Conserve' },
    { id: 'preparatory', label: 'Preparatory' },
  ];
  const phase2Posture = catalog?.decisions.phase2.engagementPosture ?? [
    { id: 'shock', label: 'Shock' },
    { id: 'methodical', label: 'Methodical' },
    { id: 'siege', label: 'Siege' },
    { id: 'feint', label: 'Feint' },
  ];
  const phase2Risk = catalog?.decisions.phase2.riskTolerance ?? [
    { id: 'low', label: 'Low' },
    { id: 'med', label: 'Med' },
    { id: 'high', label: 'High' },
  ];
  const phase3Focus = catalog?.decisions.phase3.exploitVsSecure ?? [
    { id: 'push', label: 'Push' },
    { id: 'secure', label: 'Secure' },
  ];
  const phase3End = catalog?.decisions.phase3.endState ?? [
    { id: 'capture', label: 'Capture' },
    { id: 'raid', label: 'Raid' },
    { id: 'destroy', label: 'Destroy' },
    { id: 'withdraw', label: 'Withdraw' },
  ];

  const [target, setTarget] = useState<OperationTarget>(targets[0]?.id ?? 'foundry');
  const [opType, setOpType] = useState<OperationType>(types[0]?.id ?? 'campaign');

  const [phase1, setPhase1] = useState({ axis: '', fire: '' });
  const [phase2, setPhase2] = useState({ posture: '', risk: '' });
  const [phase3, setPhase3] = useState({ focus: '', endState: '' });
  const [sections, setSections] = useState({
    overview: true,
    taskForce: false,
    operationConsole: false,
    phaseReport: false,
    aar: false,
  });

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

  const handleAckAar = async () => {
    const resp = await postAckAar();
    onActionResult(resp);
  };

  const objectives = useMemo(() => state.contestedPlanet.objectives, [state.contestedPlanet.objectives]);

  const awaitingDecision = state.operation?.awaitingDecision ?? false;
  const pendingPhase = state.operation?.pendingPhaseRecord;
  const phaseOrder = ['contact_shaping', 'engagement', 'exploit_consolidate', 'complete'];
  const currentPhaseIndex = state.operation ? phaseOrder.indexOf(state.operation.currentPhase) : -1;

  useEffect(() => {
    if (!targets.find(item => item.id === target)) {
      setTarget(targets[0]?.id ?? 'foundry');
    }
  }, [targets, target]);

  useEffect(() => {
    if (!types.find(item => item.id === opType)) {
      setOpType(types[0]?.id ?? 'campaign');
    }
  }, [types, opType]);

  useEffect(() => {
    if (pendingPhase) {
      setSections(prev => ({ ...prev, phaseReport: true }));
    }
  }, [pendingPhase]);

  useEffect(() => {
    if (state.lastAar) {
      setSections(prev => ({ ...prev, aar: true }));
    }
  }, [state.lastAar]);

  const toggleSection = (key: keyof typeof sections) => {
    setSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="p-4 md:p-6">
      <div className="nodebar-modules">
        <CollapsibleModule
          id="contested-overview"
          title="Overview"
          tone="contested"
          isOpen={sections.overview}
          onToggle={() => toggleSection('overview')}
          summary={`Control ${controlPct}% • Objectives ${objectives.map(obj => obj.status).join('/')}`}
        >
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div className="space-y-4">
              <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-4 space-y-3">
                <SectionHeader title="Planet Control" tone="contested" />
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

              <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-4 space-y-2">
                <SectionHeader title="Objectives" tone="contested" />
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
            </div>

            <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-4 space-y-3">
              <SectionHeader title="Enemy Intel" tone="contested" />
              {(['infantry', 'walkers', 'support'] as const).map(key => (
                <div key={key} className="flex items-center justify-between text-sm font-mono">
                  <span className="uppercase">{key}</span>
                  <span>
                    {state.contestedPlanet.enemy[key].min}–{state.contestedPlanet.enemy[key].max} ({state.contestedPlanet.enemy[key].actual})
                  </span>
                </div>
              ))}
              <div className="space-y-2">
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Confidence</div>
                <div className="grid grid-cols-10 gap-1">
                  {Array.from({ length: 10 }).map((_, idx) => {
                    const lit = idx < Math.round(state.contestedPlanet.enemy.intelConfidence * 10);
                    return <div key={idx} className={`h-2 rounded ${lit ? 'bg-contested' : 'bg-white/10'}`} />;
                  })}
                </div>
              </div>
            </div>
          </div>
        </CollapsibleModule>

        <CollapsibleModule
          id="contested-task-force"
          title="Task Force"
          tone="contested"
          isOpen={sections.taskForce}
          onToggle={() => toggleSection('taskForce')}
          summary={`Readiness ${Math.round(state.taskForce.readiness * 100)}% • Cohesion ${Math.round(state.taskForce.cohesion * 100)}%`}
        >
          <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-4 space-y-3">
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
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <KpiTile label="Ammo" value={state.taskForce.supplies.ammo} tone="neutral" />
              <KpiTile label="Fuel" value={state.taskForce.supplies.fuel} tone="neutral" />
              <KpiTile label="Med+Spares" value={state.taskForce.supplies.medSpares} tone="neutral" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <KpiTile label="Infantry" value={state.taskForce.composition.infantry} tone="neutral" />
              <KpiTile label="Walkers" value={state.taskForce.composition.walkers} tone="neutral" />
              <KpiTile label="Support" value={state.taskForce.composition.support} tone="neutral" />
            </div>
          </div>
        </CollapsibleModule>

        <CollapsibleModule
          id="contested-operation-console"
          title="Operation Console"
          tone="contested"
          isOpen={sections.operationConsole}
          onToggle={() => toggleSection('operationConsole')}
          summary={
            state.operation
              ? `${state.operation.currentPhase} • Day ${state.operation.dayInOperation}/${state.operation.estimatedTotalDays}`
              : 'No active operation'
          }
        >
          <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-4 space-y-4">
            {!state.operation ? (
              <div className="space-y-3">
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Launch Operation</div>
                <div className="space-y-2">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Target</div>
                  {targets.map(item => (
                    <label key={item.id} className="flex items-center gap-2 text-xs font-mono">
                      <input
                        type="radio"
                        checked={target === item.id}
                        onChange={() => setTarget(item.id)}
                      />
                      {item.label}
                    </label>
                  ))}
                </div>
                <div className="space-y-2">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Operation Type</div>
                  {types.map(item => (
                    <label key={item.id} className="flex items-center gap-2 text-xs font-mono">
                      <input
                        type="radio"
                        checked={opType === item.id}
                        onChange={() => setOpType(item.id)}
                      />
                      {item.label}
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
                <div className="text-xs font-mono text-text-secondary uppercase tracking-[0.2em]">Operation Status</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                  <div>Target: {state.operation.target}</div>
                  <div>Type: {state.operation.opType}</div>
                  <div>Phase: {state.operation.currentPhase}</div>
                  <div>Day {state.operation.dayInOperation} / {state.operation.estimatedTotalDays}</div>
                </div>
                {state.operation.latestBattleDay && (
                  <div className="space-y-2 glass-surface glass-strong glass-tone-contested glass-elev-low p-3">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Latest Battle Day</div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                      <div>Power: {state.operation.latestBattleDay.yourPower.toFixed(1)} / {state.operation.latestBattleDay.enemyPower.toFixed(1)}</div>
                      <div>Advantage: {state.operation.latestBattleDay.yourAdvantage.toFixed(2)}</div>
                      <div>Initiative: {state.operation.latestBattleDay.initiative ? 'Yes' : 'No'}</div>
                      <div>Progress Δ: {state.operation.latestBattleDay.progressDelta.toFixed(3)}</div>
                      <div>Losses: {Object.values(state.operation.latestBattleDay.yourLosses).reduce((a, b) => a + b, 0)}</div>
                      <div>Enemy Losses: {Object.values(state.operation.latestBattleDay.enemyLosses).reduce((a, b) => a + b, 0)}</div>
                    </div>
                    <div className="text-xs font-mono text-text-secondary">
                      Supply Ratios A/F/M: {state.operation.latestBattleDay.supplies.ammoRatio.toFixed(2)} / {state.operation.latestBattleDay.supplies.fuelRatio.toFixed(2)} / {state.operation.latestBattleDay.supplies.medRatio.toFixed(2)}
                    </div>
                    <div className="text-xs font-mono text-text-secondary">
                      Tags: {state.operation.latestBattleDay.tags.length > 0 ? state.operation.latestBattleDay.tags.join(', ') : 'none'}
                    </div>
                  </div>
                )}
                {state.operation.currentPhaseDays.length > 0 && (
                  <div className="space-y-1 glass-surface glass-strong glass-tone-neutral glass-elev-low p-2">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Current Phase Days</div>
                    {state.operation.currentPhaseDays.slice(-8).map(day => (
                      <div key={`${day.dayIndex}-${day.phase}`} className="text-xs font-mono text-text-secondary">
                        D{day.dayIndex}: Δ{day.progressDelta.toFixed(3)} | You {Object.values(day.yourLosses).reduce((a, b) => a + b, 0)} / Enemy {Object.values(day.enemyLosses).reduce((a, b) => a + b, 0)}
                      </div>
                    ))}
                  </div>
                )}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1 text-[10px] uppercase tracking-[0.2em] text-text-secondary">
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
                  <div className="text-xs font-mono text-text-secondary">
                    Phase report ready in the <span className="text-contested">Phase Report</span> module.
                  </div>
                ) : awaitingDecision ? (
                  <div className="space-y-3">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Phase Decisions</div>
                    {state.operation.currentPhase === 'contact_shaping' && (
                      <div className="space-y-2">
                        <RadioGroup
                          label="Approach Axis"
                          options={phase1Approach}
                          value={phase1.axis}
                          onChange={value => setPhase1(prev => ({ ...prev, axis: value }))}
                        />
                        <RadioGroup
                          label="Fire Support Prep"
                          options={phase1Fire}
                          value={phase1.fire}
                          onChange={value => setPhase1(prev => ({ ...prev, fire: value }))}
                        />
                      </div>
                    )}
                    {state.operation.currentPhase === 'engagement' && (
                      <div className="space-y-2">
                        <RadioGroup
                          label="Engagement Posture"
                          options={phase2Posture}
                          value={phase2.posture}
                          onChange={value => setPhase2(prev => ({ ...prev, posture: value }))}
                        />
                        <RadioGroup
                          label="Risk Tolerance"
                          options={phase2Risk}
                          value={phase2.risk}
                          onChange={value => setPhase2(prev => ({ ...prev, risk: value }))}
                        />
                      </div>
                    )}
                    {state.operation.currentPhase === 'exploit_consolidate' && (
                      <div className="space-y-2">
                        <RadioGroup
                          label="Focus"
                          options={phase3Focus}
                          value={phase3.focus}
                          onChange={value => setPhase3(prev => ({ ...prev, focus: value }))}
                        />
                        <RadioGroup
                          label="End State"
                          options={phase3End}
                          value={phase3.endState}
                          onChange={value => setPhase3(prev => ({ ...prev, endState: value }))}
                        />
                      </div>
                    )}
                    <button
                      onClick={submitPhase}
                      disabled={
                        (state.operation.currentPhase === 'contact_shaping' && (!phase1.axis || !phase1.fire)) ||
                        (state.operation.currentPhase === 'engagement' && (!phase2.posture || !phase2.risk)) ||
                        (state.operation.currentPhase === 'exploit_consolidate' && (!phase3.focus || !phase3.endState))
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
        </CollapsibleModule>

        <CollapsibleModule
          id="contested-phase-report"
          title="Phase Report"
          tone="contested"
          isOpen={sections.phaseReport}
          onToggle={() => toggleSection('phaseReport')}
          summary={pendingPhase ? `${pendingPhase.phase} report pending acknowledgment` : 'No pending phase report'}
        >
          {pendingPhase ? (
            <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-3 space-y-2">
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Phase Report</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                <div>Progress Δ: {pendingPhase.summary.progressDelta}</div>
                <div>Losses: {pendingPhase.summary.losses}</div>
                <div>Enemy Losses: {pendingPhase.summary.enemyLosses}</div>
                <div>Ammo: {pendingPhase.summary.suppliesSpent.ammo}</div>
                <div>Fuel: {pendingPhase.summary.suppliesSpent.fuel}</div>
                <div>Med: {pendingPhase.summary.suppliesSpent.medSpares}</div>
                <div>Readiness Δ: {pendingPhase.summary.readinessDelta}</div>
                <div>Cohesion Δ: {pendingPhase.summary.cohesionDelta}</div>
                <div>Enemy Cohesion Δ: {pendingPhase.summary.enemyCohesionDelta}</div>
              </div>
              {pendingPhase.days.length > 0 && (
                <div className="space-y-1 text-xs font-mono text-text-secondary">
                  {pendingPhase.days.map(day => (
                    <div key={`${day.dayIndex}-${day.phase}`}>
                      D{day.dayIndex}: Δ{day.progressDelta.toFixed(3)} | A/F/M {day.supplies.ammoRatio.toFixed(2)}/{day.supplies.fuelRatio.toFixed(2)}/{day.supplies.medRatio.toFixed(2)}
                    </div>
                  ))}
                </div>
              )}
              <div className="space-y-1 text-xs font-mono text-text-secondary">
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
          ) : (
            <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-3 text-xs font-mono text-text-secondary">
              No pending phase report.
            </div>
          )}
        </CollapsibleModule>

        <CollapsibleModule
          id="contested-aar"
          title="After Action Report"
          tone="contested"
          isOpen={sections.aar}
          onToggle={() => toggleSection('aar')}
          summary={state.lastAar ? `${state.lastAar.outcome} • ${state.lastAar.days}D` : 'No report available'}
        >
          {state.lastAar ? (
            <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-4 space-y-3">
              <div className="space-y-2 text-xs font-mono">
                <div>Outcome: {state.lastAar.outcome}</div>
                <div>Target: {state.lastAar.target}</div>
                <div>Op Type: {state.lastAar.operationType}</div>
                <div>Days: {state.lastAar.days}</div>
                <div>Losses: {state.lastAar.losses}</div>
                <div>Enemy Losses: {state.lastAar.enemyLosses}</div>
                <div>
                  Remaining Supplies: A{state.lastAar.remainingSupplies.ammo} / F{state.lastAar.remainingSupplies.fuel} / M{state.lastAar.remainingSupplies.medSpares}
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">Top Factors</div>
                  {state.lastAar.topFactors.map((factor, idx) => (
                    <div key={`${factor.name}-${idx}`}>
                      {factor.name}: {factor.value} ({factor.delta}) — {factor.why}
                    </div>
                  ))}
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">Phases</div>
                  {state.lastAar.phases.map((phase, idx) => (
                    <div key={`${phase.phase}-${idx}`} className="space-y-1">
                      <div>
                        {phase.phase} Day {phase.startDay}–{phase.endDay}: Progress {phase.summary.progressDelta.toFixed(3)}, Losses {phase.summary.losses}, Enemy {phase.summary.enemyLosses}
                      </div>
                      {phase.days.slice(-5).map(day => (
                        <div key={`${day.dayIndex}-${day.phase}`} className="pl-2 text-text-secondary">
                          D{day.dayIndex}: Δ{day.progressDelta.toFixed(3)} | You {Object.values(day.yourLosses).reduce((a, b) => a + b, 0)} / Enemy {Object.values(day.enemyLosses).reduce((a, b) => a + b, 0)}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
              <button
                onClick={handleAckAar}
                className="btn-action px-3 py-2 text-[10px] uppercase tracking-[0.2em] border border-contested/40 text-contested"
              >
                Acknowledge AAR
              </button>
            </div>
          ) : (
            <div className="glass-surface glass-strong glass-tone-contested glass-elev-low p-3 text-xs font-mono text-text-secondary">
              No AAR available.
            </div>
          )}
        </CollapsibleModule>
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
  options: { id: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1">
      <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">{label}</div>
      <div className="grid grid-cols-2 gap-2">
        {options.map(option => (
          <button
            key={option.id}
            type="button"
            onClick={() => onChange(option.id)}
            className={`glass-surface glass-strong glass-tone-contested px-2 py-1 text-[10px] uppercase tracking-[0.2em] ${
              value === option.id ? 'bg-contested text-space border-contested' : 'text-contested'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
