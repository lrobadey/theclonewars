import { useState, useMemo } from 'react';
import { StrategicMap } from './components/StrategicMap';
import { StatusHeader } from './components/StatusHeader';
import { SystemDrawer } from './components/SystemDrawer';
import { QueueJobModal } from './components/QueueJobModal';
import { useGameState } from './hooks/useGameState';
import { mapFromGameState } from './data/mapFromGameState';
import { AnimatePresence, motion } from 'framer-motion';

interface Toast {
  id: number;
  message: string;
}

function App() {
  const { state, loading, error } = useGameState();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activePoolType, setActivePoolType] = useState<'factory' | 'barracks' | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const mapData = useMemo(() => {
    if (!state) return { nodes: [], connections: [] };
    return mapFromGameState(state);
  }, [state]);

  const addToast = (message: string) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  };

  const handleNodeClick = (nodeId: string) => {
    if (nodeId === 'new_system_core') {
      setSelectedNodeId(nodeId);
      setIsDrawerOpen(true);
    }
  };

  const handleDrawerClose = () => {
    setIsDrawerOpen(false);
    setSelectedNodeId(null);
  };

  const handleQueueJob = (poolType: 'factory' | 'barracks') => {
    setActivePoolType(poolType);
  };

  const handleModalSubmit = (type: string, quantity: number) => {
    addToast(`${type} x${quantity} queued. Not wired yet.`);
    setActivePoolType(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-space flex items-center justify-center">
        <div className="text-text-primary font-mono animate-pulse">
          INITIALIZING STRATEGIC LINK...
        </div>
      </div>
    );
  }

  if (error || !state) {
    return (
      <div className="min-h-screen bg-space flex items-center justify-center p-8">
        <div className="text-contested font-mono border border-contested p-4 bg-contested/10">
          <h2 className="font-bold mb-2">CRITICAL SYSTEM ERROR</h2>
          <p>{error || 'Failed to establish connection to command engine.'}</p>
          <button 
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-contested text-space font-bold hover:bg-contested/80 transition-colors"
          >
            RETRY LINK
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-space relative overflow-hidden">
      {/* CRT Scanline overlay */}
      <div className="crt-overlay" />
      
      {/* Status Header */}
      <StatusHeader state={state} />
      
      {/* Main Strategic Map */}
      <main className="pt-16 px-4 md:px-8">
        <StrategicMap 
          nodes={mapData.nodes} 
          connections={mapData.connections}
          selectedNodeId={selectedNodeId || undefined}
          onNodeClick={handleNodeClick}
        />
      </main>

      {/* System Drawer */}
      <SystemDrawer 
        isOpen={isDrawerOpen}
        onClose={handleDrawerClose}
        selectedNodeId={selectedNodeId}
        state={state}
        onQueueJob={handleQueueJob}
      />

      {/* Queue Job Modal */}
      <QueueJobModal 
        isOpen={activePoolType !== null}
        onClose={() => setActivePoolType(null)}
        poolType={activePoolType}
        onSubmit={handleModalSubmit}
      />

      {/* Toasts */}
      <div className="toast-container">
        <AnimatePresence>
          {toasts.map(toast => (
            <motion.div
              key={toast.id}
              initial={{ x: 100, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 100, opacity: 0 }}
              className="toast"
            >
              <div className="w-2 h-2 bg-core rounded-full animate-pulse" />
              {toast.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default App;
