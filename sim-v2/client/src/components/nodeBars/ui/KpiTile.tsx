import type { ReactNode } from 'react';
import { GlassCard } from '../../ui/GlassCard';

interface KpiTileProps {
  label: string;
  value: string | number;
  tone?: 'core' | 'deep' | 'contested' | 'neutral';
  icon?: ReactNode;
  subLabel?: string;
}

const toneClass: Record<NonNullable<KpiTileProps['tone']>, string> = {
  core: 'text-core',
  deep: 'text-deep',
  contested: 'text-contested',
  neutral: 'text-text-primary',
};

export function KpiTile({ label, value, tone = 'neutral', icon, subLabel }: KpiTileProps) {
  return (
    <GlassCard tone={tone} elevation="low" className={`px-3 py-2 glass-strong ${toneClass[tone]}`}>
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
    </GlassCard>
  );
}
