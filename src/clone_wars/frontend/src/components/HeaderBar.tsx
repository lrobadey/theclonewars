import type { GameStateResponse } from "../api/types";
import { fmtInt, fmtPct, sumSupplies, sumUnits } from "../utils/format";

export default function HeaderBar({ state }: { state: GameStateResponse }) {
  const supplies = sumSupplies(state.logistics.depots);
  const units = sumUnits(state.logistics.depots);
  const maxCapacity =
    state.production.maxFactories * state.production.slotsPerFactory +
    state.barracks.maxBarracks * state.barracks.slotsPerBarracks;
  const currentCapacity = state.production.capacity + state.barracks.capacity;
  const icPct = maxCapacity > 0 ? currentCapacity / maxCapacity : 0;

  return (
    <div className="panel panel-live p-5 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase text-soft tracking-[0.3em]">War Simulation</p>
          <h1 className="text-2xl font-semibold">Clone Wars Command Terminal</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="glass-chip">Day {state.day}</span>
          <span className="glass-chip">AP {state.actionPoints} / 3</span>
        </div>
      </div>
      <div className="divider" />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
        <div className="space-y-1">
          <p className="text-xs text-soft uppercase tracking-[0.2em]">Industrial Capacity</p>
          <p className="text-lg">{fmtPct(icPct)} online</p>
          <p className="text-xs text-soft">
            Factories {state.production.factories}/{state.production.maxFactories} | Barracks {state.barracks.barracks}/
            {state.barracks.maxBarracks}
          </p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-soft uppercase tracking-[0.2em]">Supply Stockpile</p>
          <p>Ammo {fmtInt(supplies.ammo)} | Fuel {fmtInt(supplies.fuel)} | Med {fmtInt(supplies.medSpares)}</p>
          <p className="text-xs text-soft">Frontline supplies synced with contested front depot.</p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-soft uppercase tracking-[0.2em]">Force Totals</p>
          <p>Infantry {fmtInt(units.infantry)} | Walkers {fmtInt(units.walkers)} | Support {fmtInt(units.support)}</p>
          <p className="text-xs text-soft">Task force readiness {fmtPct(state.taskForce.readiness, 0)}</p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-soft uppercase tracking-[0.2em]">Command Pulse</p>
          <div className="flex items-center gap-3">
            <span className="pulse-dot" />
            <p className="text-sm text-soft">Faction turn: {state.factionTurn.replace(/_/g, " ")}</p>
          </div>
          <p className="text-xs text-soft">Operations resolve daily after orders are submitted.</p>
        </div>
      </div>
    </div>
  );
}
