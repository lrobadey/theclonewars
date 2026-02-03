import { motion } from 'framer-motion';

interface InlineProgressProps {
  value: number;
  tone?: 'core' | 'deep' | 'contested';
}

const toneClass: Record<NonNullable<InlineProgressProps['tone']>, string> = {
  core: 'bg-core',
  deep: 'bg-deep',
  contested: 'bg-contested',
};

export function InlineProgress({ value, tone = 'core' }: InlineProgressProps) {
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <div className="relative h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
      <motion.div
        className={`h-full ${toneClass[tone]} bar-shimmer`}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.45, ease: 'easeOut' }}
      />
    </div>
  );
}
