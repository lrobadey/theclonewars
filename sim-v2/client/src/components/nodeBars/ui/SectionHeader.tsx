interface SectionHeaderProps {
  title: string;
  tone?: 'core' | 'deep' | 'contested';
}

const toneClass: Record<NonNullable<SectionHeaderProps['tone']>, string> = {
  core: 'border-core text-core',
  deep: 'border-deep text-deep',
  contested: 'border-contested text-contested',
};

export function SectionHeader({ title, tone = 'core' }: SectionHeaderProps) {
  return (
    <h3
      className={`text-[10px] font-bold uppercase tracking-[0.2em] border-l-2 pl-2 ${toneClass[tone]}`}
    >
      {title}
    </h3>
  );
}
