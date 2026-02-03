import { useState, useMemo } from 'react';
import { StrategicMap } from './components/StrategicMap';
import { StatusHeader } from './components/StatusHeader';
import { NodeBarDrawer } from './components/nodeBars/NodeBarDrawer';
import { useGameState } from './hooks/useGameState';
import { mapFromGameState } from './data/mapFromGameState';
import { AnimatePresence, motion } from 'framer-motion';
import type { ApiResponse } from './api/types';

interface Toast {
  id: number;
  message: string;
  kind?: ApiResponse['messageKind'];
}

function App() {
  type NodeId = 'new_system_core' | 'deep_space' | 'contested_front';
  const { state, loading, error, refresh, applyApiResponse } = useGameState();
  const [selectedNodeId, setSelectedNodeId] = useState<NodeId | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const mapData = useMemo(() => {
    if (!state) return { nodes: [], connections: [] };
    return mapFromGameState(state);
  }, [state]);

  const addToast = (message: string, kind?: ApiResponse['messageKind']) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, kind }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  };

  const handleNodeClick = (nodeId: string) => {
    if (isDrawerOpen && selectedNodeId === nodeId) {
      handleDrawerClose();
      return;
    }
    setSelectedNodeId(nodeId as NodeId);
    setIsDrawerOpen(true);
  };

  const handleDrawerClose = () => {
    setIsDrawerOpen(false);
    setSelectedNodeId(null);
  };

  const handleActionResult = (resp: ApiResponse) => {
    applyApiResponse(resp);
    const message = resp.message ?? (resp.ok ? 'OK' : 'ERROR');
    addToast(message, resp.messageKind);
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
      <NodeBarDrawer 
        isOpen={isDrawerOpen}
        onClose={handleDrawerClose}
        selectedNodeId={selectedNodeId}
        state={state}
        onActionResult={handleActionResult}
        onRefresh={refresh}
      />

      {/* Toasts */}
      <div className="toast-container">
        <AnimatePresence>
          {toasts.map(toast => {
            const tone =
              toast.kind === 'error' ? 'border-contested text-contested' : toast.kind === 'accent' ? 'border-deep text-deep' : 'border-core text-core';
            return (
            <motion.div
              key={toast.id}
              initial={{ x: 100, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 100, opacity: 0 }}
              className={`toast ${tone}`}
            >
              <div className="w-2 h-2 bg-current rounded-full animate-pulse" />
              {toast.message}
            </motion.div>
          )})}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default App;
