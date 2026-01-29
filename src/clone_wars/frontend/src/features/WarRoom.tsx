import { useMemo, useState } from "react";
import type { OperationState, RaidState } from "../api/types";
import PanelShell from "../components/PanelShell";
import { fmtPct } from "../utils/format";

const PHASE1_AXIS = ["direct", "flank", "dispersed", "stealth"];
const PHASE1_FIRE = ["conserve", "preparatory"];
const PHASE2_POSTURE = ["shock", "methodical", "siege", "feint"];
const PHASE2_RISK = ["low", "med", "high"];
const PHASE3_FOCUS = ["push", "secure"];
const PHASE3_END = ["capture", "raid", "destroy", "withdraw"];

export default function WarRoom({
  operation,
  raid,
  onStartOperation,
  onSubmitPhase,
  onAcknowledgePhase,
  onAdvanceDay,
  onRaidAction
}: {
  operation: OperationState | null;
  raid: RaidState | null;
  onStartOperation: (payload: Record<string, unknown>) => void;
  onSubmitPhase: (payload: Record<string, unknown>) => void;
  onAcknowledgePhase: () => void;
  onAdvanceDay: () => void;
  onRaidAction: (action: string) => void;
}) {
  const [target, setTarget] = useState("Droid Foundry");
  const [opType, setOpType] = useState("campaign");
  const [axis, setAxis] = useState("direct");
  const [fire, setFire] = useState("preparatory");
  const [posture, setPosture] = useState("methodical");
  const [risk, setRisk] = useState("med");
  const [focus, setFocus] = useState("secure");
  const [endState, setEndState] = useState("capture");

  const phaseLabel = useMemo(() => {
    if (!operation) return "";
    if (operation.currentPhase.includes("contact")) return "Phase 1: Contact & Shaping";
    if (operation.currentPhase.includes("engagement")) return "Phase 2: Main Engagement";
    if (operation.currentPhase.includes("exploit")) return "Phase 3: Exploit & Consolidate";
    return "";
  }, [operation]);

  return (
    <PanelShell title="War Room" tone="tone-tactical">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-soft">Issue orders, resolve phases, and advance the campaign day.</p>
        <button className="control-button" onClick={onAdvanceDay}>Advance Day</button>
      </div>

      {operation ? (
        <div className="space-y-4">
          <div className="panel panel-live p-4 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-base">Active Operation</h3>
              <span className="glass-chip">{operation.opType.toUpperCase()}</span>
            </div>
            <p className="text-sm">Target: {operation.target}</p>
            <p className="text-xs text-soft">{phaseLabel} | Day {operation.dayInOperation + 1}/{operation.estimatedTotalDays}</p>
            <p className="text-xs text-soft">Awaiting decision: {operation.awaitingDecision ? "YES" : "NO"}</p>
          </div>
          {operation.pendingPhaseRecord && (
            <div className="panel panel-live p-4 space-y-2">
              <h3 className="text-base">Phase Report</h3>
              <p className="text-xs text-soft">{operation.pendingPhaseRecord.phase.toUpperCase()} resolved.</p>
              <p className="text-xs">Progress Δ {fmtPct(operation.pendingPhaseRecord.summary.progressDelta, 1)} | Losses {operation.pendingPhaseRecord.summary.losses}</p>
              <button className="control-button" onClick={onAcknowledgePhase}>Acknowledge Phase</button>
            </div>
          )}
          {operation.awaitingDecision && !operation.pendingPhaseRecord && (
            <div className="panel panel-live p-4 space-y-3">
              <h3 className="text-base">{phaseLabel} Orders</h3>
              {operation.currentPhase.includes("contact") && (
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <p className="text-soft">Approach Axis</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {PHASE1_AXIS.map((option) => (
                        <button
                          key={option}
                          className={`control-button ${axis === option ? "ring-2 ring-emerald-300" : ""}`}
                          onClick={() => setAxis(option)}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-soft">Fire Support Prep</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {PHASE1_FIRE.map((option) => (
                        <button
                          key={option}
                          className={`control-button ${fire === option ? "ring-2 ring-emerald-300" : ""}`}
                          onClick={() => setFire(option)}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              {operation.currentPhase.includes("engagement") && (
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <p className="text-soft">Engagement Posture</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {PHASE2_POSTURE.map((option) => (
                        <button
                          key={option}
                          className={`control-button ${posture === option ? "ring-2 ring-emerald-300" : ""}`}
                          onClick={() => setPosture(option)}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-soft">Risk Tolerance</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {PHASE2_RISK.map((option) => (
                        <button
                          key={option}
                          className={`control-button ${risk === option ? "ring-2 ring-emerald-300" : ""}`}
                          onClick={() => setRisk(option)}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              {operation.currentPhase.includes("exploit") && (
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <p className="text-soft">Exploit vs Secure</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {PHASE3_FOCUS.map((option) => (
                        <button
                          key={option}
                          className={`control-button ${focus === option ? "ring-2 ring-emerald-300" : ""}`}
                          onClick={() => setFocus(option)}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-soft">End State</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {PHASE3_END.map((option) => (
                        <button
                          key={option}
                          className={`control-button ${endState === option ? "ring-2 ring-emerald-300" : ""}`}
                          onClick={() => setEndState(option)}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <button
                className="control-button w-full"
                onClick={() =>
                  onSubmitPhase({
                    axis,
                    fire,
                    posture,
                    risk,
                    focus,
                    endState
                  })
                }
              >
                Submit Phase Orders
              </button>
            </div>
          )}
          {operation.phaseHistory.length > 0 && (
            <div className="panel panel-live p-4">
              <h3 className="text-base">Phase Timeline</h3>
              <div className="space-y-2 text-xs text-soft mt-2">
                {operation.phaseHistory.map((record, idx) => (
                  <p key={`${record.phase}-${idx}`}>
                    {record.phase.toUpperCase()} | Days {record.startDay}-{record.endDay} | Losses {record.summary.losses}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="panel panel-live p-4 space-y-3">
          <h3 className="text-base">Launch Operation</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <label className="text-soft">Target Objective
              <select className="input-field w-full mt-1" value={target} onChange={(e) => setTarget(e.target.value)}>
                <option>Droid Foundry</option>
                <option>Communications Array</option>
                <option>Power Plant</option>
              </select>
            </label>
            <label className="text-soft">Operation Type
              <select className="input-field w-full mt-1" value={opType} onChange={(e) => setOpType(e.target.value)}>
                <option value="campaign">Campaign</option>
                <option value="siege">Siege</option>
                <option value="raid">Raid</option>
              </select>
            </label>
          </div>
          <button className="control-button w-full" onClick={() => onStartOperation({ target, opType })}>
            Commit Operation
          </button>
        </div>
      )}

      {raid && (
        <div className="panel panel-live p-4 space-y-3">
          <h3 className="text-base">Raid Control</h3>
          <p className="text-xs text-soft">Tick {raid.tick}/{raid.maxTicks} | Outcome {raid.outcome ?? "ONGOING"}</p>
          <div className="flex gap-2">
            <button className="control-button" onClick={() => onRaidAction("tick")}>Tick Raid</button>
            <button className="control-button" onClick={() => onRaidAction("resolve")}>Resolve Raid</button>
          </div>
        </div>
      )}
    </PanelShell>
  );
}
