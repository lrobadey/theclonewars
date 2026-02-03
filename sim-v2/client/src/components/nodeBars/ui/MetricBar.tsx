import { motion } from 'framer-motion';

interface MetricBarProps {
  label: string;
  value: number;
  max: number;
  tone: 'core' | 'deep' | 'contested';
}

const toneColor: Record<MetricBarProps['tone'], string> = {
  core: 'var(--color-core)',
  deep: 'var(--color-deep)',
  contested: 'var(--color-contested)',
};

export function MetricBar({ label, value, max, tone }: MetricBarProps) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] font-mono">
        <span className="text-text-secondary uppercase tracking-[0.2em]">{label}</span>
        <span className="text-text-primary font-bold">{value.toLocaleString()}</span>
      </div>
      <div className="relative h-2 w-full rounded-full border border-white/10 bg-space/60 overflow-hidden">
        <motion.div
          className="h-full"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
          style={{ backgroundColor: toneColor[tone] }}
        />
        <div className="absolute inset-0 flex justify-between opacity-30 pointer-events-none">
          {Array.from({ length: 6 }).map((_, idx) => (
            <span key={idx} className="w-px h-full bg-white/20" />
          ))}
        </div>
      </div>
    </div>
  );
}
