import type { ReactNode } from 'react';

interface KpiTileProps {
  label: string;
  value: string | number;
  tone?: 'core' | 'deep' | 'contested' | 'neutral';
  icon?: ReactNode;
  subLabel?: string;
}

const toneClass: Record<NonNullable<KpiTileProps['tone']>, string> = {
  core: 'border-core/30 bg-core/5 text-core',
  deep: 'border-deep/30 bg-deep/5 text-deep',
  contested: 'border-contested/30 bg-contested/5 text-contested',
  neutral: 'border-white/10 bg-white/5 text-text-primary',
};

export function KpiTile({ label, value, tone = 'neutral', icon, subLabel }: KpiTileProps) {
  return (
    <div className={`rounded border px-3 py-2 ${toneClass[tone]}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {icon && <div className="text-text-secondary">{icon}</div>}
          <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
            {label}
          </div>
        </div>
        <div className="font-mono font-bold text-lg text-text-primary">{value}</div>
      </div>
      {subLabel && (
        <div className="mt-1 text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
          {subLabel}
        </div>
      )}
    </div>
  );
}
