import MapVizStrip from "./MapVizStrip";

const MODES = [
  { id: "core", label: "Core Worlds", tone: "core" },
  { id: "deep", label: "Deep Space", tone: "deep" },
  { id: "tactical", label: "Contested System", tone: "tactical" }
] as const;

export default function Navigator({
  active,
  onSelect
}: {
  active: string;
  onSelect: (mode: string) => void;
}) {
  return (
    <div className="panel panel-live p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg">Theater Navigator</h2>
        <span className="glass-chip">View</span>
      </div>
      <MapVizStrip
        compact
        ariaLabel="Theater navigation"
        nodes={MODES.map((mode) => ({
          id: mode.id,
          label: mode.label,
          tone: mode.tone,
          selected: active === mode.id
        }))}
        onSelect={onSelect}
      />
      <p className="text-xs text-soft">Switch views without spending action points.</p>
    </div>
  );
}
