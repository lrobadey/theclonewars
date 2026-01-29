import { useRef, useState } from "react";
import HeaderBar from "./components/HeaderBar";
import MessageLog from "./components/MessageLog";
import Navigator from "./components/Navigator";
import TerminalContainer from "./components/TerminalContainer";
import AARViewer from "./features/AARViewer";
import LogisticsPanel from "./features/LogisticsPanel";
import ProductionPanel from "./features/ProductionPanel";
import TaskForcePanel from "./features/TaskForcePanel";
import TacticalOverview from "./features/TacticalOverview";
import WarRoom from "./features/WarRoom";
import { useGameState } from "./hooks/useGameState";
import PanelShell from "./components/PanelShell";

function useBeep(enabled: boolean) {
  const ctxRef = useRef<AudioContext | null>(null);

  return (tone: "info" | "error" | "accent") => {
    if (!enabled) return;
    if (!ctxRef.current) {
      ctxRef.current = new AudioContext();
    }
    const ctx = ctxRef.current;
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();

    const freqMap = {
      info: 420,
      accent: 620,
      error: 240
    };
    oscillator.type = "sine";
    oscillator.frequency.value = freqMap[tone];

    gain.gain.value = 0.05;
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);

    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.start();
    oscillator.stop(ctx.currentTime + 0.14);
  };
}

type TheaterMode = "core" | "deep" | "tactical";

export default function App() {
  const { state, loading, error, send, messages, pushMessage } = useGameState();
  const [theater, setTheater] = useState<TheaterMode>("tactical");
  const [showHelp, setShowHelp] = useState(false);
  const [soundOn, setSoundOn] = useState(false);
  const beep = useBeep(soundOn);

  const sendWithSound = async (path: string, payload?: Record<string, unknown>) => {
    const res = await send(path, payload);
    if (res.messageKind) {
      beep(res.messageKind);
    }
    return res;
  };

  if (loading && !state) {
    return (
      <TerminalContainer>
        <div className="panel panel-live p-6">Loading operational feed...</div>
      </TerminalContainer>
    );
  }

  if (error && !state) {
    return (
      <TerminalContainer>
        <div className="panel panel-live p-6 text-alert">{error}</div>
      </TerminalContainer>
    );
  }

  if (!state) {
    return null;
  }

  return (
    <TerminalContainer>
      <HeaderBar state={state} />
      <div className="mt-6 space-y-6">
        <Navigator active={theater} onSelect={(mode) => setTheater(mode as TheaterMode)} />

        {theater === "core" && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
            <div className="xl:col-span-9 space-y-6">
              <ProductionPanel
                production={state.production}
                barracks={state.barracks}
                onQueueProduction={(payload) => sendWithSound("/actions/production", payload)}
                onQueueBarracks={(payload) => sendWithSound("/actions/barracks", payload)}
                onUpgradeFactory={() => sendWithSound("/actions/upgrade-factory")}
                onUpgradeBarracks={() => sendWithSound("/actions/upgrade-barracks")}
              />
            </div>
            <div className="xl:col-span-3 space-y-6">
              <MessageLog messages={messages} />
              <PanelShell title="System Controls">
                <div className="space-y-3 text-sm">
                  <button className="control-button w-full" onClick={() => setShowHelp(true)}>
                    Open Command Primer
                  </button>
                  <button
                    className="control-button w-full"
                    onClick={() => {
                      setSoundOn((prev) => {
                        const next = !prev;
                        pushMessage(`Audio cues ${next ? "enabled" : "disabled"}`, "info");
                        return next;
                      });
                    }}
                  >
                    Audio Cues: {soundOn ? "On" : "Off"}
                  </button>
                </div>
              </PanelShell>
            </div>
          </div>
        )}

        {theater === "deep" && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
            <div className="xl:col-span-9 space-y-6">
              <LogisticsPanel
                logistics={state.logistics}
                onDispatch={(payload) => sendWithSound("/actions/dispatch", payload)}
              />
            </div>
            <div className="xl:col-span-3 space-y-6">
              <MessageLog messages={messages} />
              <PanelShell title="System Controls">
                <div className="space-y-3 text-sm">
                  <button className="control-button w-full" onClick={() => setShowHelp(true)}>
                    Open Command Primer
                  </button>
                  <button
                    className="control-button w-full"
                    onClick={() => {
                      setSoundOn((prev) => {
                        const next = !prev;
                        pushMessage(`Audio cues ${next ? "enabled" : "disabled"}`, "info");
                        return next;
                      });
                    }}
                  >
                    Audio Cues: {soundOn ? "On" : "Off"}
                  </button>
                </div>
              </PanelShell>
            </div>
          </div>
        )}

        {theater === "tactical" && (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
            <div className="xl:col-span-4 space-y-6">
              <TacticalOverview contested={state.contestedPlanet} />
              <TaskForcePanel state={state} />
              <MessageLog messages={messages} />
              <PanelShell title="System Controls">
                <div className="space-y-3 text-sm">
                  <button className="control-button w-full" onClick={() => setShowHelp(true)}>
                    Open Command Primer
                  </button>
                  <button
                    className="control-button w-full"
                    onClick={() => {
                      setSoundOn((prev) => {
                        const next = !prev;
                        pushMessage(`Audio cues ${next ? "enabled" : "disabled"}`, "info");
                        return next;
                      });
                    }}
                  >
                    Audio Cues: {soundOn ? "On" : "Off"}
                  </button>
                </div>
              </PanelShell>
            </div>
            <div className="xl:col-span-8 space-y-6">
              <WarRoom
                operation={state.operation}
                raid={state.raid}
                onStartOperation={(payload) => sendWithSound("/actions/operation/start", payload)}
                onSubmitPhase={(payload) => sendWithSound("/actions/operation/decisions", payload)}
                onAcknowledgePhase={() => sendWithSound("/actions/operation/ack-phase")}
                onAdvanceDay={() => sendWithSound("/actions/advance-day")}
                onRaidAction={(action) => sendWithSound(`/actions/raid/${action}`)}
              />
              {state.lastAar && (
                <AARViewer report={state.lastAar} onClose={() => sendWithSound("/actions/ack-aar")} />
              )}
            </div>
          </div>
        )}
      </div>

      {showHelp && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="panel panel-live max-w-2xl p-6 space-y-4">
            <h2 className="text-xl">Command Primer</h2>
            <p className="text-sm text-soft">
              Use the Theater Navigator to shift between Core Worlds, Deep Space, and the Contested System. Queue
              production in Core, dispatch shipments in Deep Space, and prosecute operations from the War Room.
            </p>
            <ul className="text-xs text-soft space-y-1">
              <li>Operations resolve in phases. Submit orders when prompted to continue.</li>
              <li>Advance the day after orders are set to process logistics and production.</li>
              <li>After-action reports detail the numeric drivers of success or failure.</li>
            </ul>
            <button className="control-button" onClick={() => setShowHelp(false)}>
              Close Primer
            </button>
          </div>
        </div>
      )}
    </TerminalContainer>
  );
}
