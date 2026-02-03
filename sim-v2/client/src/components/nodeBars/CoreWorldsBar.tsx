import { useMemo, useState } from 'react';
import type { ApiResponse, GameStateResponse } from '../../api/types';
import { postQueueProduction, postQueueBarracks, postUpgradeFactory, postUpgradeBarracks } from '../../api/client';
import { Chip } from './ui/Chip';
import { MetricBar } from './ui/MetricBar';
import { KpiTile } from './ui/KpiTile';
import { SectionHeader } from './ui/SectionHeader';

interface CoreWorldsBarProps {
  state: GameStateResponse;
  onActionResult: (resp: ApiResponse) => void;
}

type ProductionJobType = 'ammo' | 'fuel' | 'med_spares' | 'walkers';
type BarracksJobType = 'infantry' | 'support';

const JOB_LABELS: Record<ProductionJobType | BarracksJobType, string> = {
  ammo: 'Ammo',
  fuel: 'Fuel',
  med_spares: 'Med+Spares',
  walkers: 'Walkers',
  infantry: 'Infantry',
  support: 'Support',
};

function toJobKey(job: string) {
  return job.replace(/[\s+]/g, '_').toLowerCase();
}

export function CoreWorldsBar({ state, onActionResult }: CoreWorldsBarProps) {
  const [productionModalOpen, setProductionModalOpen] = useState(false);
  const [barracksModalOpen, setBarracksModalOpen] = useState(false);
  const [jobType, setJobType] = useState<ProductionJobType | BarracksJobType>('ammo');
  const [quantity, setQuantity] = useState(100);

  const coreDepot = state.logistics.depots.find(d => d.id === 'new_system_core');
  const supplies = coreDepot?.supplies ?? { ammo: 0, fuel: 0, medSpares: 0 };
  const units = coreDepot?.units ?? { infantry: 0, walkers: 0, support: 0 };

  const mergedJobs = useMemo(() => {
    const jobs = [...state.production.jobs, ...state.barracks.jobs].map(job => ({
      ...job,
      sortKey: job.etaDays === -1 ? 99999 : job.etaDays,
    }));
    return jobs.sort((a, b) => a.sortKey - b.sortKey || a.type.localeCompare(b.type));
  }, [state.production.jobs, state.barracks.jobs]);

  const submitProduction = async () => {
    const resp = await postQueueProduction(jobType as ProductionJobType, quantity);
    onActionResult(resp);
    setProductionModalOpen(false);
  };

  const submitBarracks = async () => {
    const resp = await postQueueBarracks(jobType as BarracksJobType, quantity);
    onActionResult(resp);
    setBarracksModalOpen(false);
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
    <div className="nodebar-grid grid grid-cols-1 md:grid-cols-3 gap-6 p-6">
      <div className="space-y-4">
        <SectionHeader title="Logistics: Stockpiles" tone="core" />
        <div className="space-y-4">
          <MetricBar label="Fuel" value={supplies.fuel} max={5000} tone="core" />
          <MetricBar label="Ammo" value={supplies.ammo} max={5000} tone="deep" />
          <MetricBar label="Med+Spares" value={supplies.medSpares} max={5000} tone="contested" />
        </div>
      </div>

      <div className="space-y-4">
        <SectionHeader title="Production: Industry" tone="core" />
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[10px] text-text-secondary font-mono uppercase tracking-[0.2em]">Factories</div>
              <div className="text-sm font-bold text-text-primary font-mono">
                {state.production.factories}/{state.production.maxFactories}{' '}
                <span className="text-[10px] text-text-secondary font-normal">
                  {state.production.capacity} slots • {state.production.slotsPerFactory}/factory
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setJobType('ammo');
                  setQuantity(100);
                  setProductionModalOpen(true);
                }}
                className="btn-action px-2 py-1 text-[10px] uppercase border border-core/40 text-core"
              >
                + Queue Factory Job
              </button>
              <button
                onClick={handleUpgradeFactory}
                className="btn-action px-2 py-1 text-[10px] uppercase border border-core/40 text-core"
              >
                Upgrade Factory
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <div className="text-[10px] text-text-secondary font-mono uppercase tracking-[0.2em]">Barracks</div>
              <div className="text-sm font-bold text-text-primary font-mono">
                {state.barracks.barracks}/{state.barracks.maxBarracks}{' '}
                <span className="text-[10px] text-text-secondary font-normal">
                  {state.barracks.capacity} slots • {state.barracks.slotsPerBarracks}/barracks
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setJobType('infantry');
                  setQuantity(100);
                  setBarracksModalOpen(true);
                }}
                className="btn-action px-2 py-1 text-[10px] uppercase border border-core/40 text-core"
              >
                + Queue Barracks Job
              </button>
              <button
                onClick={handleUpgradeBarracks}
                className="btn-action px-2 py-1 text-[10px] uppercase border border-core/40 text-core"
              >
                Upgrade Barracks
              </button>
            </div>
          </div>
        </div>

        <div className="rounded border border-core/10 bg-space/40 p-3 h-48 overflow-y-auto">
          <div className="flex items-center justify-between mb-2">
            <div className="text-[10px] font-bold text-core/70 uppercase tracking-[0.2em]">Active Queue</div>
            <Chip label="Production" tone="core" size="sm" />
          </div>
          <div className="space-y-2">
            {mergedJobs.length === 0 ? (
              <div className="text-xs text-text-secondary italic text-center py-6 opacity-60">
                No active production jobs
              </div>
            ) : (
              mergedJobs.map((job, idx) => (
                <div
                  key={`${job.type}-${idx}`}
                  className="flex items-center justify-between text-[11px] font-mono border-b border-white/5 pb-1"
                >
                  <span className="text-text-primary uppercase">
                    {toJobKey(job.type).replace(/_/g, ' ')} ×{job.quantity}
                  </span>
                  <span className="text-core/80">
                    ETA: {job.etaDays === -1 ? '?' : `${job.etaDays}D`} • {job.stopAt}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <SectionHeader title="Strategic Reserve: Garrison" tone="core" />
        <div className="grid grid-cols-1 gap-3">
          <KpiTile
            label="Infantry"
            value={units.infantry.toLocaleString()}
            tone="neutral"
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="8" r="4" />
                <path d="M6 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
              </svg>
            }
          />
          <KpiTile
            label="Walkers"
            value={units.walkers.toLocaleString()}
            tone="neutral"
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="4" y="7" width="16" height="8" rx="2" />
                <path d="M6 15v4M18 15v4M10 7V4h4v3" />
              </svg>
            }
          />
          <KpiTile
            label="Support"
            value={units.support.toLocaleString()}
            tone="neutral"
            icon={
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v6M9 5h6" />
                <circle cx="12" cy="14" r="6" />
              </svg>
            }
          />
        </div>
      </div>

      {productionModalOpen && (
        <ModalShell title="Queue Factory Job" onClose={() => setProductionModalOpen(false)}>
          <JobForm
            options={['ammo', 'fuel', 'med_spares', 'walkers']}
            jobType={jobType}
            quantity={quantity}
            onChangeType={setJobType}
            onChangeQuantity={setQuantity}
            onSubmit={submitProduction}
          />
        </ModalShell>
      )}
      {barracksModalOpen && (
        <ModalShell title="Queue Barracks Job" onClose={() => setBarracksModalOpen(false)}>
          <JobForm
            options={['infantry', 'support']}
            jobType={jobType}
            quantity={quantity}
            onChangeType={setJobType}
            onChangeQuantity={setQuantity}
            onSubmit={submitBarracks}
          />
        </ModalShell>
      )}
    </div>
  );
}

function ModalShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      <div className="modal-overlay absolute inset-0 bg-space/60 backdrop-blur-sm" onClick={onClose} />
      <div className="modal-content relative w-full max-w-md border border-core/40 bg-space shadow-[0_0_40px_rgba(0,212,255,0.15)]">
        <div className="flex items-center justify-between px-5 py-3 border-b border-core/20">
          <div className="text-core font-bold tracking-[0.3em] text-xs uppercase">{title}</div>
          <button onClick={onClose} className="text-core/70 hover:text-core">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

function JobForm({
  options,
  jobType,
  quantity,
  onChangeType,
  onChangeQuantity,
  onSubmit,
}: {
  options: Array<ProductionJobType | BarracksJobType>;
  jobType: ProductionJobType | BarracksJobType;
  quantity: number;
  onChangeType: (value: ProductionJobType | BarracksJobType) => void;
  onChangeQuantity: (value: number) => void;
  onSubmit: () => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
          Job Type
        </label>
        <div className="grid grid-cols-2 gap-2 mt-2">
          {options.map(option => (
            <button
              key={option}
              onClick={() => onChangeType(option)}
              className={`px-3 py-2 text-xs font-mono border uppercase ${
                jobType === option ? 'bg-core text-space border-core' : 'border-core/30 text-core'
              }`}
              type="button"
            >
              {JOB_LABELS[option]}
            </button>
          ))}
        </div>
      </div>
      <div>
        <label className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
          Quantity
        </label>
        <input
          type="number"
          min={1}
          value={quantity}
          onChange={e => onChangeQuantity(Number(e.target.value))}
          className="mt-2 w-full bg-space border border-core/30 p-2 text-text-primary font-mono focus:border-core outline-none"
        />
      </div>
      <button
        onClick={onSubmit}
        className="w-full py-3 font-bold tracking-[0.2em] bg-core text-space hover:bg-core/80"
        type="button"
      >
        QUEUE ORDER
      </button>
    </div>
  );
}
