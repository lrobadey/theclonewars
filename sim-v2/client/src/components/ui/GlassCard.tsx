import type { PropsWithChildren } from 'react';
import { GlassSurface, type GlassSurfaceProps } from './GlassSurface';

interface GlassCardProps extends Omit<GlassSurfaceProps, 'children'> {
  dense?: boolean;
}

export function GlassCard({
  dense = false,
  className,
  children,
  ...rest
}: PropsWithChildren<GlassCardProps>) {
  const classes = [dense ? 'glass-strong' : '', className ?? ''].filter(Boolean).join(' ');

  return (
    <GlassSurface className={classes} {...rest}>
      {children}
    </GlassSurface>
  );
}
