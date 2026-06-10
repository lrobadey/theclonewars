import { useMemo, useState } from 'react';
import type { ApiResponse, GameStateResponse } from '../../api/types';
import { postQueueBarracks, postQueueProduction, postUpgradeBarracks, postUpgradeFactory } from '../../api/client';
import { Chip } from './ui/Chip';
import { InlineProgress } from './ui/InlineProgress';
import { KpiTile } from './ui/KpiTile';
import { SectionHeader } from './ui/SectionHeader';
import { GlassCard } from '../ui/GlassCard';

interface CoreWorldsBarProps {
  state: GameStateResponse;
  onActionResult: (resp: ApiResponse) => void;
}

type FactoryJobType = 'ammo' | 'fuel' | 'med_spares' | 'walkers';
type BarracksJobType = 'infantry' | 'support';

const FACTORY_JOBS: FactoryJobType[] = ['ammo', 'fuel', 'med_spares', 'walkers'];
const BARRACKS_JOBS: BarracksJobType[] = ['infantry', 'support'];

function labelForJobType(type: string) {
  return type.replace(/_/g, ' ');
}

function jobCost(type: string, state: GameStateResponse) {
  return state.production.costs[type] ?? state.barracks.costs[type] ?? 1;
}

function jobProgress(job: { type: string; quantity: number; remaining: number }, state: GameStateResponse) {
  const total = Math.max(1, job.quantity * jobCost(job.type, state));
  return 1 - job.remaining / total;
}

export function CoreWorldsBar({ state, onActionResult }: CoreWorldsBarProps) {
  const [quantity, setQuantity] = useState(100);
  const coreDepot = state.logistics.depots.find(depot => depot.id === 'new_system_core');
  const stockpiles = coreDepot?.supplies ?? { ammo: 0, fuel: 0, medSpares: 0 };
  const reserve = coreDepot?.units ?? { infantry: 0, walkers: 0, support: 0 };

  const activeJobs = useMemo(
    () =>
      [...state.production.jobs, ...state.barracks.jobs].sort((a, b) => {
        if (a.etaDays !== b.etaDays) return a.etaDays - b.etaDays;
        return a.type.localeCompare(b.type);
      }),
    [state.barracks.jobs, state.production.jobs]
  );

  const queueFactory = async (jobType: FactoryJobType) => {
    const resp = await postQueueProduction(jobType, quantity);
    onActionResult(resp);
  };

  const queueBarracks = async (jobType: BarracksJobType) => {
    const resp = await postQueueBarracks(jobType, quantity);
    onActionResult(resp);
  };

  const handleUpgradeFactory = async () => {
    const resp = await postUpgradeFactory();
    onActionResult(resp);
  };

  const handleUpgradeBarracks = async () => {
    const resp = await postUpgradeBarracks();
    onActionResult(resp);
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <KpiTile label="Factories" value={`${state.production.factories}/${state.production.maxFactories}`} tone="core" />
        <KpiTile label="Barracks" value={`${state.barracks.barracks}/${state.barracks.maxBarracks}`} tone="core" />
        <KpiTile label="Queue" value={activeJobs.length} tone="neutral" />
        <KpiTile label="Reserve" value={reserve.infantry + reserve.walkers + reserve.support} tone="neutral" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <GlassCard tone="core" elevation="low" className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionHeader title="Industrial Pool" tone="core" />
            <Chip label={`Batch ${quantity}`} tone="neutral" />
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-[120px_1fr] sm:items-end">
            <label className="space-y-1">
              <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">Batch size</div>
              <input
                type="number"
                min="1"
                max="9999"
                value={quantity}
                onChange={event => setQuantity(Math.max(1, Number(event.target.value) || 1))}
                className="w-full rounded border border-white/10 bg-space/60 px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-core/60"
              />
            </label>

            <div className="grid gap-2 sm:grid-cols-2">
              <button type="button" onClick={handleUpgradeFactory} className="btn-action rounded border border-core/30 px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-core">
                Upgrade Factory
              </button>
              <button type="button" onClick={handleUpgradeBarracks} className="btn-action rounded border border-core/30 px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-core">
                Upgrade Barracks
              </button>
            </div>
          </div>

          <div className="mt-4 grid gap-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <GlassCard tone="core" elevation="low" className="p-3">
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Factory Orders</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {FACTORY_JOBS.map(job => (
                    <button
                      key={job}
                      type="button"
                      onClick={() => queueFactory(job)}
                      className="btn-action rounded border border-core/30 px-3 py-1.5 text-[10px] uppercase tracking-[0.18em] text-core"
                    >
                      {labelForJobType(job)}
                    </button>
                  ))}
                </div>
              </GlassCard>

              <GlassCard tone="core" elevation="low" className="p-3">
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">Barracks Orders</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {BARRACKS_JOBS.map(job => (
                    <button
                      key={job}
                      type="button"
                      onClick={() => queueBarracks(job)}
                      className="btn-action rounded border border-core/30 px-3 py-1.5 text-[10px] uppercase tracking-[0.18em] text-core"
                    >
                      {labelForJobType(job)}
                    </button>
                  ))}
                </div>
              </GlassCard>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <KpiTile label="Ammo" value={stockpiles.ammo.toLocaleString()} tone="core" />
              <KpiTile label="Fuel" value={stockpiles.fuel.toLocaleString()} tone="core" />
              <KpiTile label="Med+Spares" value={stockpiles.medSpares.toLocaleString()} tone="core" />
            </div>
          </div>
        </GlassCard>

        <GlassCard tone="core" elevation="low" className="p-4">
          <SectionHeader title="Queues" tone="core" />
          <div className="mt-4 space-y-3">
            {activeJobs.length === 0 ? (
              <div className="rounded border border-white/10 bg-white/5 px-3 py-4 text-sm text-text-secondary">
                No active production jobs.
              </div>
            ) : (
              activeJobs.map(job => (
                <div key={`${job.type}-${job.stopAt}-${job.quantity}-${job.remaining}`} className="space-y-2 rounded border border-white/10 bg-space/40 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">
                        {labelForJobType(job.type)} x{job.quantity}
                      </div>
                      <div className="text-xs text-text-secondary">
                        Stop at {job.stopAt}
                      </div>
                    </div>
                    <Chip label={`ETA ${job.etaDays === -1 ? '?' : `${job.etaDays}D`}`} tone={job.etaDays === -1 ? 'warn' : 'neutral'} />
                  </div>
                  <InlineProgress value={jobProgress(job, state)} tone="core" />
                  <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">
                    {job.remaining.toLocaleString()} work remaining
                  </div>
                </div>
              ))
            )}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
