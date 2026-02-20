import type { HTMLAttributes } from 'react';

export type GlassTone = 'neutral' | 'core' | 'deep' | 'contested';
export type GlassElevation = 'low' | 'mid' | 'high';

export interface GlassSurfaceProps extends HTMLAttributes<HTMLDivElement> {
  tone?: GlassTone;
  elevation?: GlassElevation;
  interactive?: boolean;
  blur?: boolean;
  highlight?: boolean;
}

const toneClass: Record<GlassTone, string> = {
  neutral: 'glass-tone-neutral',
  core: 'glass-tone-core',
  deep: 'glass-tone-deep',
  contested: 'glass-tone-contested',
};

const elevationClass: Record<GlassElevation, string> = {
  low: 'glass-elev-low',
  mid: 'glass-elev-mid',
  high: 'glass-elev-high',
};

export function GlassSurface({
  tone = 'neutral',
  elevation = 'mid',
  interactive = false,
  blur = false,
  highlight = false,
  className,
  ...rest
}: GlassSurfaceProps) {
  const classes = [
    'glass-surface',
    toneClass[tone],
    elevationClass[elevation],
    blur ? 'glass-blur' : '',
    highlight ? 'glass-highlight' : '',
    interactive ? 'transition-transform duration-200 hover:-translate-y-px' : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');

  return <div className={classes} {...rest} />;
}
