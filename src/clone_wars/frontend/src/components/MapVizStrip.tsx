type MapVizTone = "core" | "deep" | "tactical";

export type MapVizNode = {
  id: string;
  label: string;
  tone: MapVizTone;
  selected?: boolean;
  description?: string;
};

export default function MapVizStrip({
  nodes,
  onSelect,
  compact = false,
  className = "",
  ariaLabel = "System map"
}: {
  nodes: MapVizNode[];
  onSelect?: (id: string) => void;
  compact?: boolean;
  className?: string;
  ariaLabel?: string;
}) {
  return (
    <div
      className={`map-viz ${compact ? "map-viz--compact" : ""} ${className}`.trim()}
      role="group"
      aria-label={ariaLabel}
    >
      <div className="map-viz__track" aria-hidden="true" />
      {nodes.map((node) => (
        <button
          key={node.id}
          type="button"
          className={`map-viz__node map-viz__node--${node.tone} ${node.selected ? "map-viz__node--selected" : ""}`}
          onClick={() => onSelect?.(node.id)}
          aria-pressed={node.selected}
          title={node.description}
        >
          <span className="map-viz__icon" aria-hidden="true" />
          <span className="map-viz__label">{node.label}</span>
        </button>
      ))}
    </div>
  );
}
