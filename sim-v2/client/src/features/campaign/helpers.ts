import type { CatalogOption } from '../../api/types';

export function formatPct(value: number, digits = 0) {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatSigned(value: number, digits = 2) {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(digits)}`;
}

export function phaseLabel(phase: string) {
  if (phase === 'contact_shaping') return 'Contact & Shaping';
  if (phase === 'engagement') return 'Main Engagement';
  if (phase === 'exploit_consolidate') return 'Exploit & Consolidate';
  if (phase === 'complete') return 'Complete';
  return phase.replace(/_/g, ' ');
}

export function toneForObjective(status: string): 'good' | 'warn' | 'danger' {
  if (status === 'secured') return 'good';
  if (status === 'contested') return 'warn';
  return 'danger';
}

export function impactToChips(option: CatalogOption) {
  const impact = option.impact;
  if (!impact) return [];
  return [
    { label: `Progress ${formatSigned(impact.progress ?? 0, 2)}`, tone: (impact.progress ?? 0) >= 0 ? 'good' : 'warn' },
    { label: `Losses ${formatSigned(impact.losses ?? 0, 2)}`, tone: (impact.losses ?? 0) <= 0 ? 'good' : 'danger' },
    { label: `Variance ${formatSigned(impact.variance ?? 0, 2)}`, tone: Math.abs(impact.variance ?? 0) <= 0.02 ? 'good' : 'warn' },
    { label: `Supply ${formatSigned(impact.supplies ?? 0, 2)}`, tone: (impact.supplies ?? 0) <= 0 ? 'good' : 'warn' },
    { label: `Fort ${formatSigned(impact.fortification ?? 0, 2)}`, tone: (impact.fortification ?? 0) >= 0 ? 'good' : 'warn' },
  ];
}
