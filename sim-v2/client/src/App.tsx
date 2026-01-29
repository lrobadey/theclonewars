import { StrategicMap } from './components/StrategicMap';
import { StatusHeader } from './components/StatusHeader';
import { mockMapState } from './data/mockMapData';

// TODO: Wire live state in a follow-up — swap mock for getState() from api/client
// and map response to MapState when /api/state is extended or /api/map exists.

function App() {
  return (
    <div className="min-h-screen bg-space relative overflow-hidden">
      {/* CRT Scanline overlay */}
      <div className="crt-overlay" />
      
      {/* Status Header */}
      <StatusHeader data={mockMapState.header} />
      
      {/* Main Strategic Map */}
      <main className="pt-16 px-4 md:px-8">
        <StrategicMap 
          nodes={mockMapState.nodes} 
          connections={mockMapState.connections}
        />
      </main>
    </div>
  );
}

export default App;
