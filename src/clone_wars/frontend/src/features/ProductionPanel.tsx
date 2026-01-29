import { useMemo, useState } from "react";
import type { BarracksState, ProductionState } from "../api/types";
import PanelShell from "../components/PanelShell";
import { fmtInt, labelize } from "../utils/format";

const FACTORY_JOBS = [
  { id: "ammo", label: "Ammo" },
  { id: "fuel", label: "Fuel" },
  { id: "med_spares", label: "Med+Spares" },
  { id: "walkers", label: "Walkers" }
];

const BARRACKS_JOBS = [
  { id: "infantry", label: "Infantry" },
  { id: "support", label: "Support" }
];

export default function ProductionPanel({
  production,
  barracks,
  onQueueProduction,
  onQueueBarracks,
  onUpgradeFactory,
  onUpgradeBarracks
}: {
  production: ProductionState;
  barracks: BarracksState;
  onQueueProduction: (payload: Record<string, unknown>) => void;
  onQueueBarracks: (payload: Record<string, unknown>) => void;
  onUpgradeFactory: () => void;
  onUpgradeBarracks: () => void;
}) {
  const [tab, setTab] = useState<"factory" | "barracks">("factory");
  const [prodJob, setProdJob] = useState(FACTORY_JOBS[0].id);
  const [prodQty, setProdQty] = useState(10);
  const [barracksJob, setBarracksJob] = useState(BARRACKS_JOBS[0].id);
  const [barracksQty, setBarracksQty] = useState(20);

  const prodJobs = useMemo(() => production.jobs, [production.jobs]);
  const barracksJobs = useMemo(() => barracks.jobs, [barracks.jobs]);

  return (
    <PanelShell title="Production & Industry" tone="tone-core">
      <div className="flex flex-wrap gap-2">
        <button className={`control-button ${tab === "factory" ? "ring-2 ring-emerald-300" : ""}`} onClick={() => setTab("factory")}>
          Factory
        </button>
        <button className={`control-button ${tab === "barracks" ? "ring-2 ring-emerald-300" : ""}`} onClick={() => setTab("barracks")}>
          Barracks
        </button>
      </div>
      {tab === "factory" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-soft">
              Capacity {production.capacity} slots/day ({production.factories}/{production.maxFactories} factories)
            </p>
            <button className="control-button" onClick={onUpgradeFactory}>
              Upgrade Factory
            </button>
          </div>
          <div className="panel panel-live p-4 space-y-3">
            <h3 className="text-base">Queue Job</h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <label className="text-soft">Job Type
                <select className="input-field w-full mt-1" value={prodJob} onChange={(e) => setProdJob(e.target.value)}>
                  {FACTORY_JOBS.map((job) => (
                    <option key={job.id} value={job.id}>{job.label}</option>
                  ))}
                </select>
              </label>
              <label className="text-soft">Quantity
                <input
                  className="input-field w-full mt-1"
                  type="number"
                  min={1}
                  value={prodQty}
                  onChange={(e) => setProdQty(Number(e.target.value))}
                />
              </label>
            </div>
            <button
              className="control-button w-full"
              onClick={() => onQueueProduction({ jobType: prodJob, quantity: prodQty })}
            >
              Queue Production
            </button>
          </div>
          <div className="panel panel-live p-4 space-y-2">
            <h3 className="text-base">Factory Queue</h3>
            {prodJobs.length === 0 && <p className="text-xs text-soft">No factory jobs queued.</p>}
            <div className="space-y-2 text-xs">
              {prodJobs.map((job, idx) => (
                <div key={`${job.type}-${idx}`} className="flex items-center justify-between">
                  <span>{labelize(job.type)} x{fmtInt(job.quantity)}</span>
                  <span className="text-soft">ETA {job.etaDays <= 0 ? "?" : `${job.etaDays}d`}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
            <p className="text-soft">
              Capacity {barracks.capacity} slots/day ({barracks.barracks}/{barracks.maxBarracks} barracks)
            </p>
            <button className="control-button" onClick={onUpgradeBarracks}>
              Upgrade Barracks
            </button>
          </div>
          <div className="panel panel-live p-4 space-y-3">
            <h3 className="text-base">Queue Job</h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <label className="text-soft">Job Type
                <select className="input-field w-full mt-1" value={barracksJob} onChange={(e) => setBarracksJob(e.target.value)}>
                  {BARRACKS_JOBS.map((job) => (
                    <option key={job.id} value={job.id}>{job.label}</option>
                  ))}
                </select>
              </label>
              <label className="text-soft">Quantity
                <input
                  className="input-field w-full mt-1"
                  type="number"
                  min={1}
                  value={barracksQty}
                  onChange={(e) => setBarracksQty(Number(e.target.value))}
                />
              </label>
            </div>
            <button
              className="control-button w-full"
              onClick={() => onQueueBarracks({ jobType: barracksJob, quantity: barracksQty })}
            >
              Queue Barracks Job
            </button>
          </div>
          <div className="panel panel-live p-4 space-y-2">
            <h3 className="text-base">Barracks Queue</h3>
            {barracksJobs.length === 0 && <p className="text-xs text-soft">No barracks jobs queued.</p>}
            <div className="space-y-2 text-xs">
              {barracksJobs.map((job, idx) => (
                <div key={`${job.type}-${idx}`} className="flex items-center justify-between">
                  <span>{labelize(job.type)} x{fmtInt(job.quantity)}</span>
                  <span className="text-soft">ETA {job.etaDays <= 0 ? "?" : `${job.etaDays}d`}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </PanelShell>
  );
}
