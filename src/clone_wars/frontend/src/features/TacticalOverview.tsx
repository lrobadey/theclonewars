import type { ContestedPlanet } from "../api/types";
import PanelShell from "../components/PanelShell";
import { fmtPct } from "../utils/format";

const STATUS_TONE: Record<string, string> = {
  enemy: "text-alert",
  contested: "text-yellow-400",
  secured: "text-emerald-300"
};

export default function TacticalOverview({ contested }: { contested: ContestedPlanet }) {
  const intelPct = Math.round(contested.enemy.intelConfidence * 100);

  return (
    <PanelShell title="Contested System" tone="tone-tactical">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <span className="glass-chip">Control {fmtPct(contested.control, 0)}</span>
        <div className="flex items-center gap-2 text-xs text-soft uppercase tracking-[0.2em]">
          <span>Intel</span>
          <div className="confidence-bar w-24">
            <div className="confidence-bar__fill" style={{ width: `${Math.max(intelPct, 4)}%` }} />
          </div>
          <span>{fmtPct(contested.enemy.intelConfidence, 0)}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="panel panel-live p-4">
          <h3 className="text-base">Objectives</h3>
          <div className="space-y-2 mt-3">
            {contested.objectives.map((obj) => (
              <div key={obj.id} className="flex items-center justify-between">
                <span className="text-sm uppercase tracking-[0.2em]">{obj.label}</span>
                <span className={`text-xs font-semibold ${STATUS_TONE[obj.status]}`}>
                  {obj.status.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel panel-live p-4">
          <h3 className="text-base">Enemy Profile</h3>
          <p className="text-xs text-soft mt-1">Ranges widen when intel confidence is low.</p>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <div>
              Infantry: {contested.enemy.infantry.min}-{contested.enemy.infantry.max}
            </div>
            <div>
              Walkers: {contested.enemy.walkers.min}-{contested.enemy.walkers.max}
            </div>
            <div>
              Support: {contested.enemy.support.min}-{contested.enemy.support.max}
            </div>
            <div>Fortification: {contested.enemy.fortification.toFixed(2)}</div>
            <div>Reinforcement: {contested.enemy.reinforcementRate.toFixed(2)}</div>
            <div>Cohesion: {contested.enemy.cohesion.toFixed(2)}</div>
          </div>
        </div>
      </div>
    </PanelShell>
  );
}

