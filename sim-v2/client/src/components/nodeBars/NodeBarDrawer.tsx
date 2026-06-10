import { AnimatePresence, motion } from 'framer-motion';
import type { ApiResponse, CatalogResponse, GameStateResponse } from '../../api/types';
import { postAdvanceDay } from '../../api/client';
import { GlassSurface } from '../ui/GlassSurface';
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

const NODE_META: Record<NodeId, { title: string; subtitle: string; tone: 'core' | 'deep' | 'contested' }> = {
  new_system_core: {
    title: 'CORE WORLDS',
    subtitle: 'Industrial throughput and reserve management',
    tone: 'core',
  },
  deep_space: {
    title: 'DEEP SPACE',
    subtitle: 'Routes, shipments, interdiction, and transit',
    tone: 'deep',
  },
  contested_front: {
    title: 'CONTESTED SYSTEM',
    subtitle: 'Objectives, force posture, and operation control',
    tone: 'contested',
  },
};

export function NodeBarDrawer({
  isOpen,
  selectedNodeId,
  state,
  catalog,
  onClose,
  onActionResult,
  onRefresh,
}: NodeBarDrawerProps) {
  const meta = selectedNodeId ? NODE_META[selectedNodeId] : null;

  const handleAdvanceDay = async () => {
    const resp = await postAdvanceDay();
    onActionResult(resp);
  };

  return (
    <AnimatePresence>
      {isOpen && selectedNodeId && meta && (
        <motion.aside
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 26, stiffness: 220, mass: 0.9 }}
          className="fixed bottom-0 left-0 right-0 z-40 overflow-hidden"
        >
          <GlassSurface
            tone={meta.tone}
            elevation="high"
            blur
            highlight
            className="mx-3 mb-3 md:mx-6 md:mb-6 border border-white/10 shadow-[0_-18px_60px_rgba(0,0,0,0.35)]"
          >
            <div className="flex flex-col gap-4 border-b border-white/10 px-4 py-4 md:flex-row md:items-center md:justify-between md:px-6">
              <div>
                <div className="text-[10px] uppercase tracking-[0.28em] text-text-secondary font-mono">
                  {meta.title}
                </div>
                <div className="text-sm text-text-primary md:text-base">
                  {meta.subtitle}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={onRefresh}
                  className="btn-action rounded border border-white/10 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-text-secondary hover:text-text-primary hover:border-white/30"
                >
                  Refresh
                </button>
                <button
                  type="button"
                  onClick={handleAdvanceDay}
                  className="btn-action rounded border border-white/10 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-text-primary hover:border-white/30"
                >
                  Advance Day
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Close node panel"
                  className="btn-action rounded border border-white/10 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-text-secondary hover:text-text-primary hover:border-white/30"
                >
                  Close
                </button>
              </div>
            </div>

            <div className="max-h-[42vh] overflow-y-auto px-3 py-4 md:max-h-[45vh] md:px-4">
              {selectedNodeId === 'new_system_core' && <CoreWorldsBar state={state} onActionResult={onActionResult} />}
              {selectedNodeId === 'deep_space' && <DeepSpaceBar state={state} onActionResult={onActionResult} />}
              {selectedNodeId === 'contested_front' && (
                <ContestedSystemBar state={state} catalog={catalog} onActionResult={onActionResult} />
              )}
            </div>
          </GlassSurface>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
