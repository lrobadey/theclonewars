import { useState } from "react";
import type { ContestedPlanet, SystemNode } from "../api/types";
import { fmtPct } from "../utils/format";
import MapVizStrip from "../components/MapVizStrip";
import PanelShell from "../components/PanelShell";

const STATUS_TONE: Record<string, string> = {
  enemy: "text-alert",
  contested: "text-yellow-400",
  secured: "text-emerald-300"
};

export default function SystemMap({
  nodes,
  selectedNode,
  onSelect,
  contested
}: {
  nodes: SystemNode[];
  selectedNode: string;
  onSelect: (id: string) => void;
  contested: ContestedPlanet;
}) {
  const [zoom, setZoom] = useState<"system" | "planet">("system");
  const toggleZoom = () => setZoom((prev) => (prev === "system" ? "planet" : "system"));
  const intelPct = Math.round(contested.enemy.intelConfidence * 100);

  return (
    <PanelShell title="Situation Map" tone="tone-tactical">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="glass-chip">Control {fmtPct(contested.control, 0)}</span>
          <div className="flex items-center gap-2 text-xs text-soft uppercase tracking-[0.2em]">
            <span>Intel</span>
            <div className="confidence-bar w-24">
              <div className="confidence-bar__fill" style={{ width: `${Math.max(intelPct, 4)}%` }} />
            </div>
            <span>{fmtPct(contested.enemy.intelConfidence, 0)}</span>
          </div>
        </div>
        <button className="control-button" onClick={toggleZoom}>
          Zoom: {zoom === "system" ? "System" : "Planet"}
        </button>
      </div>
      <MapVizStrip
        ariaLabel="System chain"
        nodes={nodes.map((node) => ({
          id: node.id,
          label: node.label,
          tone: node.kind,
          selected: selectedNode === node.id,
          description: node.description
        }))}
        onSelect={onSelect}
      />
      {zoom === "system" ? (
        <div className="relative h-[260px] mt-2">
          <svg className="absolute inset-0 w-full h-full" aria-hidden="true">
            <defs>
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="10"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(126, 232, 255, 0.45)" />
              </marker>
            </defs>
            {nodes.map((node, idx) => {
              const next = nodes[idx + 1];
              if (!next) return null;
              return (
                <line
                  key={`${node.id}-${next.id}`}
                  x1={`${node.position.x}%`}
                  y1={`${node.position.y}%`}
                  x2={`${next.position.x}%`}
                  y2={`${next.position.y}%`}
                  className="route-line"
                />
              );
            })}
          </svg>
          {nodes.map((node) => (
            <div
              key={node.id}
              className={`map-node ${selectedNode === node.id ? "active" : ""}`}
              style={{ left: `${node.position.x}%`, top: `${node.position.y}%`, position: "absolute" }}
              onClick={() => onSelect(node.id)}
              title={node.description}
            >
              {node.label}
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="panel panel-live p-4">
              <h3 className="text-base">Objectives</h3>
              <div className="space-y-2 mt-3">
                {contested.objectives.map((obj) => (
                  <div key={obj.id} className="flex items-center justify-between">
                    <span className="text-sm uppercase tracking-[0.2em]">{obj.label}</span>
                    <span className={`text-xs font-semibold ${STATUS_TONE[obj.status]}`}>{obj.status.toUpperCase()}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="panel panel-live p-4">
              <h3 className="text-base">Enemy Profile</h3>
              <p className="text-xs text-soft mt-1">Strength range derived from intel confidence.</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div>Infantry: {contested.enemy.infantry.min}-{contested.enemy.infantry.max}</div>
                <div>Walkers: {contested.enemy.walkers.min}-{contested.enemy.walkers.max}</div>
                <div>Support: {contested.enemy.support.min}-{contested.enemy.support.max}</div>
                <div>Fortification: {contested.enemy.fortification.toFixed(2)}</div>
                <div>Reinforcement: {contested.enemy.reinforcementRate.toFixed(2)}</div>
                <div>Cohesion: {contested.enemy.cohesion.toFixed(2)}</div>
              </div>
            </div>
          </div>
          <div className="panel panel-live p-4 space-y-3">
            <h3 className="text-base">Selected Node</h3>
            {nodes.map((node) => (
              <button
                key={node.id}
                className={`control-button w-full text-left ${selectedNode === node.id ? "ring-2 ring-emerald-300" : ""}`}
                onClick={() => onSelect(node.id)}
              >
                <span className="block text-xs text-soft">{node.kind.toUpperCase()} NODE</span>
                {node.label}
              </button>
            ))}
            <p className="text-xs text-soft">Hover system nodes for quick intel. Select to inspect depot stock.</p>
          </div>
        </div>
      )}
    </PanelShell>
  );
}
