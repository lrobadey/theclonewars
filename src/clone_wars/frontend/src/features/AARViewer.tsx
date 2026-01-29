import type { AfterActionReport, RaidReport } from "../api/types";
import PanelShell from "../components/PanelShell";
import { fmtInt } from "../utils/format";

export default function AARViewer({ report, onClose }: { report: AfterActionReport | RaidReport; onClose: () => void }) {
  if (report.kind === "raid") {
    return (
      <PanelShell title="After-Action Report" tone="tone-tactical">
        <div className="space-y-3 text-sm">
          <p>Outcome: <span className="font-semibold">{report.outcome}</span> — {report.reason}</p>
          <p>Target: {report.target} | Ticks: {report.ticks}</p>
          <p>Losses: {fmtInt(report.yourCasualties)} | Enemy Losses: {fmtInt(report.enemyCasualties)}</p>
          <p>Supplies Used: Ammo {fmtInt(report.suppliesUsed.ammo)} Fuel {fmtInt(report.suppliesUsed.fuel)} Med {fmtInt(report.suppliesUsed.medSpares)}</p>
          <div>
            <h4 className="text-xs uppercase tracking-[0.2em] text-soft">Top Factors</h4>
            <ul className="text-xs text-soft space-y-1">
              {report.topFactors.map((factor, idx) => (
                <li key={`${factor.name}-${idx}`}>{factor.name} ({factor.value.toFixed(2)}): {factor.why}</li>
              ))}
            </ul>
          </div>
          <button className="control-button" onClick={onClose}>Acknowledge</button>
        </div>
      </PanelShell>
    );
  }

  return (
    <PanelShell title="After-Action Report" tone="tone-tactical">
      <div className="space-y-3 text-sm">
        <p>Outcome: <span className="font-semibold">{report.outcome}</span></p>
        <p>Target: {report.target} | Operation: {report.operationType} | Days: {report.days}</p>
        <p>Losses: {fmtInt(report.losses)}</p>
        <p>Remaining Supplies: Ammo {fmtInt(report.remainingSupplies.ammo)} Fuel {fmtInt(report.remainingSupplies.fuel)} Med {fmtInt(report.remainingSupplies.medSpares)}</p>
        <div>
          <h4 className="text-xs uppercase tracking-[0.2em] text-soft">Top Factors</h4>
          <ul className="text-xs text-soft space-y-1">
            {report.topFactors.map((factor, idx) => (
              <li key={`${factor.name}-${idx}`}>{factor.name} ({factor.value.toFixed(2)}): {factor.why}</li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="text-xs uppercase tracking-[0.2em] text-soft">Phase Timeline</h4>
          <ul className="text-xs text-soft space-y-1">
            {report.phases.map((phase, idx) => (
              <li key={`${phase.phase}-${idx}`}>
                {phase.phase.toUpperCase()} — Days {phase.startDay}-{phase.endDay} | Losses {phase.summary.losses}
              </li>
            ))}
          </ul>
        </div>
        <button className="control-button" onClick={onClose}>Acknowledge</button>
      </div>
    </PanelShell>
  );
}
