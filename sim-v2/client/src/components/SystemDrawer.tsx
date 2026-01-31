import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GameStateResponse } from '../api/types';

interface SystemDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  selectedNodeId: string | null;
  state: GameStateResponse;
  onQueueJob: (poolType: 'factory' | 'barracks') => void;
}

export function SystemDrawer({ isOpen, onClose, selectedNodeId, state, onQueueJob }: SystemDrawerProps) {
  // Only Core Worlds opens the drawer for now
  const isCore = selectedNodeId === 'new_system_core';
  
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  if (!isCore) return null;

  const coreDepot = state.logistics.depots.find(d => d.id === 'new_system_core');
  const supplies = coreDepot?.supplies || { ammo: 0, fuel: 0, medSpares: 0 };
  const units = coreDepot?.units || { infantry: 0, walkers: 0, support: 0 };
  const production = state.production;
  const barracks = state.barracks;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="system-drawer fixed bottom-0 left-0 right-0 z-40 bg-space/90 backdrop-blur-md border-t border-core/50 shadow-2xl overflow-hidden"
          style={{ maxHeight: '45vh' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-core/20">
            <div className="flex items-center gap-4">
              <div className="w-3 h-3 bg-core rounded-full animate-pulse shadow-[0_0_8px_#00D4FF]" />
              <h2 className="text-xl font-bold tracking-widest text-core font-mono">
                CORE WORLDS COMMAND DEPOT
              </h2>
            </div>
            <button 
              onClick={onClose}
              className="p-2 hover:bg-core/10 text-core rounded-full transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-8 overflow-y-auto" style={{ maxHeight: 'calc(45vh - 70px)' }}>
            
            {/* Column 1: Resources */}
            <div className="drawer-section">
              <h3 className="text-xs font-bold text-text-secondary tracking-[0.2em] mb-4 uppercase border-l-2 border-core pl-2">
                Logistics: Stockpiles
              </h3>
              <div className="space-y-4">
                <ResourceBar label="FUEL" value={supplies.fuel} max={5000} color="#00D4FF" />
                <ResourceBar label="AMMO" value={supplies.ammo} max={5000} color="#FFB800" />
                <ResourceBar label="MED+SPARES" value={supplies.medSpares} max={5000} color="#FF3B3B" />
              </div>
            </div>

            {/* Column 2: Facilities */}
            <div className="drawer-section">
              <h3 className="text-xs font-bold text-text-secondary tracking-[0.2em] mb-4 uppercase border-l-2 border-core pl-2">
                Production: Capacity
              </h3>
              <div className="space-y-3 mb-6">
                <FacilityRow 
                  label="FACTORIES" 
                  count={production.factories} 
                  max={production.maxFactories} 
                  capacity={`${production.capacity} slots/day`}
                  onAdd={() => onQueueJob('factory')}
                />
                <FacilityRow 
                  label="BARRACKS" 
                  count={barracks.barracks} 
                  max={barracks.maxBarracks} 
                  capacity={`${barracks.capacity} slots/day`}
                  onAdd={() => onQueueJob('barracks')}
                />
              </div>

              <div className="bg-space/40 rounded border border-core/10 p-3 h-32 overflow-y-auto">
                <h4 className="text-[10px] font-bold text-core/60 mb-2 uppercase">Active Queues</h4>
                <div className="space-y-2">
                  {[...production.jobs, ...barracks.jobs].length === 0 ? (
                    <div className="text-xs text-text-secondary italic text-center py-4 opacity-50">
                      No active production jobs
                    </div>
                  ) : (
                    [...production.jobs, ...barracks.jobs].map((job, i) => (
                      <div key={i} className="flex items-center justify-between text-[11px] font-mono border-b border-white/5 pb-1">
                        <span className="text-text-primary uppercase">{job.type} ×{job.quantity}</span>
                        <span className="text-core/80">ETA: {job.etaDays}D</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Column 3: Garrison */}
            <div className="drawer-section">
              <h3 className="text-xs font-bold text-text-secondary tracking-[0.2em] mb-4 uppercase border-l-2 border-core pl-2">
                Strategic Reserve: Garrison
              </h3>
              <div className="grid grid-cols-1 gap-3">
                <UnitCard label="INFANTRY" count={units.infantry} icon="👤" />
                <UnitCard label="WALKERS" count={units.walkers} icon="🤖" />
                <UnitCard label="SUPPORT" count={units.support} icon="⚙️" />
              </div>
            </div>

          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function ResourceBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] font-mono">
        <span className="text-text-secondary">{label}</span>
        <span className="text-text-primary font-bold">{value.toLocaleString()}</span>
      </div>
      <div className="h-1.5 w-full bg-space/60 rounded-full overflow-hidden border border-white/5">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          className="h-full shadow-[0_0_4px_currentColor]"
          style={{ backgroundColor: color, color: color }}
        />
      </div>
    </div>
  );
}

function FacilityRow({ label, count, max, capacity, onAdd }: { label: string; count: number; max: number; capacity: string; onAdd: () => void }) {
  return (
    <div className="flex items-center justify-between group">
      <div>
        <div className="text-[10px] text-text-secondary font-mono mb-0.5">{label}</div>
        <div className="text-sm font-bold text-text-primary font-mono">
          {count}/{max} <span className="text-[10px] font-normal text-text-secondary ml-1">{capacity}</span>
        </div>
      </div>
      <button 
        onClick={onAdd}
        className="text-[10px] font-bold px-2 py-1 border border-core/30 text-core hover:bg-core hover:text-space transition-all rounded uppercase tracking-tighter"
      >
        + Queue
      </button>
    </div>
  );
}

function UnitCard({ label, count, icon }: { label: string; count: number; icon: string }) {
  return (
    <div className="bg-core/5 border border-core/20 rounded p-3 flex items-center justify-between group hover:border-core/50 transition-colors">
      <div className="flex items-center gap-3">
        <span className="text-xl opacity-80 group-hover:opacity-100 transition-opacity">{icon}</span>
        <span className="text-xs font-bold text-text-primary tracking-wider">{label}</span>
      </div>
      <div className="text-lg font-mono font-bold text-core">{count.toLocaleString()}</div>
    </div>
  );
}
