type ChipTone = 'core' | 'deep' | 'contested' | 'neutral' | 'good' | 'warn' | 'danger';

interface ChipProps {
  label: string;
  tone?: ChipTone;
  size?: 'sm' | 'md';
  pulse?: boolean;
}

const toneClass: Record<ChipTone, string> = {
  core: 'border-core/40 text-core bg-core/10',
  deep: 'border-deep/40 text-deep bg-deep/10',
  contested: 'border-contested/40 text-contested bg-contested/10',
  neutral: 'border-white/20 text-text-secondary bg-white/5',
  good: 'border-core/40 text-core bg-core/10',
  warn: 'border-deep/40 text-deep bg-deep/10',
  danger: 'border-contested/40 text-contested bg-contested/10',
};

export function Chip({ label, tone = 'neutral', size = 'sm', pulse }: ChipProps) {
  const base = 'inline-flex items-center gap-1 rounded-full border font-mono uppercase tracking-[0.18em]';
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-[9px]' : 'px-3 py-1 text-[10px]';
  const pulseClass = pulse ? ' chip-pulse' : '';
  return (
    <span
      className={`${base} ${sizeClass} ${toneClass[tone]}${pulseClass}`}
    >
      {label}
    </span>
  );
}
