import type { ReactNode } from 'react';

interface CollapsibleModuleProps {
  id: string;
  title: string;
  tone: 'core' | 'deep' | 'contested';
  summary?: ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}

export function CollapsibleModule({
  id,
  title,
  tone,
  summary,
  isOpen,
  onToggle,
  children,
}: CollapsibleModuleProps) {
  return (
    <section className={`nodebar-module glass-surface glass-strong glass-tone-${tone} glass-elev-low`}>
      <button
        type="button"
        className="nodebar-module-header"
        onClick={onToggle}
        aria-expanded={isOpen}
        aria-controls={id}
      >
        <div className="space-y-1">
          <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">{title}</div>
          {summary && <div className="text-xs text-text-secondary font-mono">{summary}</div>}
        </div>
        <span className={`nodebar-module-chevron ${isOpen ? 'open' : ''}`} aria-hidden>
          ▾
        </span>
      </button>
      {isOpen && (
        <div id={id} className="nodebar-module-body">
          {children}
        </div>
      )}
    </section>
  );
}
