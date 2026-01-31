import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface QueueJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  poolType: 'factory' | 'barracks' | null;
  onSubmit: (type: string, quantity: number) => void;
}

const JOB_TYPES = {
  factory: ['Ammo', 'Fuel', 'Med+Spares', 'Walkers'],
  barracks: ['Infantry', 'Support']
};

export function QueueJobModal({ isOpen, onClose, poolType, onSubmit }: QueueJobModalProps) {
  const [selectedType, setSelectedType] = useState('');
  const [quantity, setQuantity] = useState(100);

  if (!poolType) return null;

  const types = JOB_TYPES[poolType];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedType) return;
    onSubmit(selectedType, quantity);
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-space/60 backdrop-blur-sm z-[60]"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-[70] bg-space border border-core shadow-[0_0_50px_rgba(0,212,255,0.2)] overflow-hidden"
          >
            <div className="bg-core/10 px-6 py-4 border-b border-core/30 flex justify-between items-center">
              <h3 className="text-core font-bold tracking-widest uppercase">
                New {poolType} Order
              </h3>
              <button onClick={onClose} className="text-core/60 hover:text-core">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] text-text-secondary uppercase tracking-widest font-bold">
                  Resource Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {types.map(t => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setSelectedType(t)}
                      className={`px-3 py-2 text-xs font-mono border transition-all ${
                        selectedType === t 
                        ? 'bg-core text-space border-core' 
                        : 'border-core/30 text-core hover:border-core'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] text-text-secondary uppercase tracking-widest font-bold">
                  Target Quantity
                </label>
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(Number(e.target.value))}
                  className="w-full bg-space border border-core/30 p-3 text-text-primary font-mono focus:border-core outline-none transition-colors"
                  placeholder="Enter quantity..."
                  min="1"
                />
              </div>

              <button
                type="submit"
                disabled={!selectedType}
                className={`w-full py-4 font-bold tracking-[0.2em] transition-all ${
                  selectedType 
                  ? 'bg-core text-space hover:bg-core/80 shadow-[0_0_20px_rgba(0,212,255,0.3)]' 
                  : 'bg-white/5 text-white/20 cursor-not-allowed'
                }`}
              >
                QUEUE WORK ORDER
              </button>
              
              <p className="text-[9px] text-center text-text-secondary italic">
                Note: All orders are subject to industrial slot availability.
              </p>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
