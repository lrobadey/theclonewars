import { useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ApiResponse, CatalogResponse, GameStateResponse } from '../../api/types';
import { postAdvanceDay } from '../../api/client';
import { Chip } from './ui/Chip';
import { CoreWorldsBar } from './CoreWorldsBar';
import { DeepSpaceBar } from './DeepSpaceBar';
import { ContestedSystemBar } from './ContestedSystemBar';

type NodeId = 'new_system_core' | 'deep_space' | 'contested_front';

interface NodeBarDrawerProps {
  isOpen: boolean;
  selectedNodeId: NodeId | null;
  state: GameStateResponse;
  catalog: CatalogResponse | null;
  onClose: () => void;
  onActionResult: (resp: ApiResponse) => void;
  onRefresh: () => void;
}

const NODE_META: Record<
  NodeId,
  { title: string; subtitle: string; tone: 'core' | 'deep' | 'contested'; dotClass: string }
> = {
  new_system_core: {
    title: 'CORE WORLDS',
    subtitle: 'Command_Depot | new_system_core',
    tone: 'core',
    dotClass: 'bg-core text-core',
  },
  deep_space: {
    title: 'DEEP SPACE',
    subtitle: 'Transit_Command | deep_space',
    tone: 'deep',
    dotClass: 'bg-deep text-deep',
  },
  contested_front: {
    title: 'CONTESTED SYSTEM',
    subtitle: 'Frontline_Command | contested_front',
    tone: 'contested',
    dotClass: 'bg-contested text-contested',
  },
};

function statusFromRisk(risk: number) {
  if (risk > 0.6) return 'danger';
  if (risk > 0.3) return 'warn';
  return 'good';
}

export function NodeBarDrawer({
  isOpen,
  selectedNodeId,
  state,
  catalog,
  onClose,
  onActionResult,
  onRefresh,
}: NodeBarDrawerProps) {
  const mapNode = selectedNodeId
    ? state.mapView?.nodes.find(node => node.id === selectedNodeId) ?? null
    : null;
  const meta = mapNode
    ? {
        title: mapNode.label,
        subtitle: mapNode.subtitle1,
        tone: mapNode.type,
        dotClass: mapNode.type === 'core' ? 'bg-core text-core' : mapNode.type === 'contested' ? 'bg-contested text-contested' : 'bg-deep text-deep',
      }
    : selectedNodeId
      ? NODE_META[selectedNodeId]
      : null;
  const glassToneClass =
    meta?.tone === 'core'
      ? 'glass-tone-core'
      : meta?.tone === 'deep'
        ? 'glass-tone-deep'
        : meta?.tone === 'contested'
          ? 'glass-tone-contested'
          : 'glass-tone-neutral';

  const routeHealth = useMemo(() => {
    const counts = { active: 0, disrupted: 0, blocked: 0, severity: 'good' as 'good' | 'warn' | 'danger' };
    state.logistics.routes.forEach(route => {
      if (route.interdictionRisk > 0.6) counts.blocked += 1;
      else if (route.interdictionRisk > 0.3) counts.disrupted += 1;
      else counts.active += 1;
    });
    const maxRisk = Math.max(0, ...state.logistics.routes.map(route => route.interdictionRisk));
    counts.severity = statusFromRisk(maxRisk);
    return counts;
  }, [state.logistics.routes]);

  useEffect(() => {
    if (!isOpen) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  const handleAdvanceDay = async () => {
    const resp = await postAdvanceDay();
    onActionResult(resp);
  };

  return (
    <AnimatePresence>
      {isOpen && selectedNodeId && meta && (
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 26, stiffness: 220, mass: 0.9 }}
          className={`nodebar-shell glass-surface glass-blur glass-strong glass-elev-high ${glassToneClass} fixed bottom-0 left-0 right-0 z-40 overflow-hidden flex flex-col ${meta.tone}`}
        >
          <div className={`nodebar-header glass-surface glass-strong glass-elev-low ${glassToneClass} relative m-2 px-6 py-4 border-b border-white/10`}>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close node bar"
              title="Close"
              className="btn-action absolute right-3 top-3 grid h-8 w-8 place-items-center rounded border border-white/10 text-text-secondary hover:text-text-primary hover:border-white/30"
            >
              <span aria-hidden className="text-lg leading-none">
                ×
              </span>
            </button>

            <div className="flex items-center gap-4 pr-10">
              <div className={`w-3 h-3 rounded-full shadow-[0_0_10px_currentColor] ${meta.dotClass}`} />
              <div>
                <div className="text-xs text-text-secondary font-mono uppercase tracking-[0.28em]">
                  {meta.title}
                </div>
                <div className="text-[11px] text-text-secondary font-mono uppercase tracking-[0.18em]">
                  {meta.subtitle}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 nodebar-chiprow">
              <Chip
                label={`Routes ${routeHealth.active}/${routeHealth.disrupted}/${routeHealth.blocked}`}
                tone={routeHealth.severity}
                pulse={routeHealth.severity !== 'good'}
              />
              <Chip label={`AP ${state.actionPoints}`} tone="neutral" />
              <Chip label={`DAY ${state.day}`} tone="neutral" />
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={onRefresh}
                className="btn-action px-3 py-1 text-[10px] uppercase tracking-[0.2em] border border-white/10 text-text-secondary hover:text-text-primary"
              >
                Refresh
              </button>
              <button
                onClick={handleAdvanceDay}
                className="btn-action px-3 py-1 text-[10px] uppercase tracking-[0.2em] border border-white/10 text-text-primary hover:border-white/30"
              >
                Advance Day
              </button>
            </div>
          </div>

          <div className="nodebar-content overflow-y-auto px-2 pb-2">
            <AnimatePresence mode="wait">
              {selectedNodeId === 'new_system_core' && (
                <motion.div
                  key="core"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0, transition: { duration: 0.22, ease: 'easeOut' } }}
                  exit={{ opacity: 0, y: 12, transition: { duration: 0.16, ease: 'easeIn' } }}
                >
                  <CoreWorldsBar state={state} onActionResult={onActionResult} />
                </motion.div>
              )}
              {selectedNodeId === 'deep_space' && (
                <motion.div
                  key="deep"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0, transition: { duration: 0.22, ease: 'easeOut' } }}
                  exit={{ opacity: 0, y: 12, transition: { duration: 0.16, ease: 'easeIn' } }}
                >
                  <DeepSpaceBar state={state} onActionResult={onActionResult} />
                </motion.div>
              )}
              {selectedNodeId === 'contested_front' && (
                <motion.div
                  key="contested"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0, transition: { duration: 0.22, ease: 'easeOut' } }}
                  exit={{ opacity: 0, y: 12, transition: { duration: 0.16, ease: 'easeIn' } }}
                >
                  <ContestedSystemBar state={state} catalog={catalog} onActionResult={onActionResult} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
