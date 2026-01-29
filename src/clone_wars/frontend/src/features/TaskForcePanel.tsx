import type { GameStateResponse } from "../api/types";
import PanelShell from "../components/PanelShell";
import { fmtInt, fmtPct } from "../utils/format";

export default function TaskForcePanel({ state }: { state: GameStateResponse }) {
  const tf = state.taskForce;
  return (
    <PanelShell title="Task Force" tone="tone-tactical">
      <div className="space-y-2 text-sm">
        <p>Location: {tf.location.replace(/_/g, " ")}</p>
        <p>Readiness: {fmtPct(tf.readiness, 0)} | Cohesion: {fmtPct(tf.cohesion, 0)}</p>
        <div className="text-xs text-soft space-y-1">
          <p>Infantry {fmtInt(tf.composition.infantry)}</p>
          <p>Walkers {fmtInt(tf.composition.walkers)}</p>
          <p>Support {fmtInt(tf.composition.support)}</p>
          <p>Supplies Ammo {fmtInt(tf.supplies.ammo)} Fuel {fmtInt(tf.supplies.fuel)} Med {fmtInt(tf.supplies.medSpares)}</p>
        </div>
      </div>
    </PanelShell>
  );
}
