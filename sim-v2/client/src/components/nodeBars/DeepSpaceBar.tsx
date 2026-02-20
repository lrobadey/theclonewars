import { useMemo, useState } from 'react';
import type { ApiResponse, GameStateResponse } from '../../api/types';
import { postDispatchShipment } from '../../api/client';
import { Chip } from './ui/Chip';
import { InlineProgress } from './ui/InlineProgress';
import { KpiTile } from './ui/KpiTile';
import { SectionHeader } from './ui/SectionHeader';
import { GlassSurface } from '../ui/GlassSurface';
import { CollapsibleModule } from './ui/CollapsibleModule';

interface DeepSpaceBarProps {
  state: GameStateResponse;
  onActionResult: (resp: ApiResponse) => void;
}

type DispatchPayload = {
  origin: string;
  destination: string;
  supplies: { ammo: number; fuel: number; medSpares: number };
  units: { infantry: number; walkers: number; support: number };
};

function statusFromRisk(risk: number) {
  if (risk > 0.6) return 'blocked';
  if (risk > 0.3) return 'disrupted';
  return 'active';
}

function getReachableDestinations(
  origin: string,
  routes: GameStateResponse['logistics']['routes']
): string[] {
  const graph = new Map<string, string[]>();
  for (const route of routes) {
    const next = graph.get(route.origin) ?? [];
    next.push(route.destination);
    graph.set(route.origin, next);
  }

  const queue: string[] = [origin];
  const visited = new Set<string>([origin]);
  const reachable: string[] = [];

  while (queue.length > 0) {
    const node = queue.shift();
    if (!node) break;
    for (const next of graph.get(node) ?? []) {
      if (visited.has(next)) continue;
      visited.add(next);
      reachable.push(next);
      queue.push(next);
    }
  }

  return reachable;
}

export function DeepSpaceBar({ state, onActionResult }: DeepSpaceBarProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [payload, setPayload] = useState<DispatchPayload>({
    origin: '',
    destination: '',
    supplies: { ammo: 0, fuel: 0, medSpares: 0 },
    units: { infantry: 0, walkers: 0, support: 0 },
  });
  const [sections, setSections] = useState({
    overview: true,
    shipments: false,
    orders: false,
    fleet: false,
    transitLog: false,
  });

  const routeCounts = useMemo(() => {
    return state.logistics.routes.reduce(
      (acc, route) => {
        const status = statusFromRisk(route.interdictionRisk);
        acc[status] += 1;
        return acc;
      },
      { active: 0, disrupted: 0, blocked: 0 }
    );
  }, [state.logistics.routes]);

  const routeHealth = useMemo(() => {
    const maxRisk = Math.max(0, ...state.logistics.routes.map(route => route.interdictionRisk));
    if (maxRisk > 0.6) return 'danger';
    if (maxRisk > 0.3) return 'warn';
    return 'good';
  }, [state.logistics.routes]);

  const origins = state.logistics.depots.map(depot => depot.id);
  const destinations = useMemo(() => {
    if (!payload.origin) return [];
    return getReachableDestinations(payload.origin, state.logistics.routes);
  }, [payload.origin, state.logistics.routes]);

  const canDispatch =
    payload.origin &&
    payload.destination &&
    (payload.supplies.ammo +
      payload.supplies.fuel +
      payload.supplies.medSpares +
      payload.units.infantry +
      payload.units.walkers +
      payload.units.support >
      0);

  const toggleSection = (key: keyof typeof sections) => {
    setSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleDispatch = async () => {
    if (!canDispatch) return;
    const resp = await postDispatchShipment(payload);
    onActionResult(resp);
    setModalOpen(false);
  };

  return (
    <div className="p-4 md:p-6">
      <div className="nodebar-modules">
        <CollapsibleModule
          id="deep-overview"
          title="Overview"
          tone="deep"
          isOpen={sections.overview}
          onToggle={() => toggleSection('overview')}
          summary={`Routes A/D/B ${routeCounts.active}/${routeCounts.disrupted}/${routeCounts.blocked}`}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <KpiTile label="Active Orders" value={state.logistics.activeOrders.length} tone="neutral" />
            <KpiTile label="In-Transit Shipments" value={state.logistics.shipments.length} tone="neutral" />
            <KpiTile label="Cargo Ships" value={state.logistics.ships.length} tone="neutral" />
            <KpiTile label="Route Health" value={routeHealth.toUpperCase()} tone="neutral" />
          </div>
          <div className="glass-surface glass-strong glass-tone-deep glass-elev-low p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <SectionHeader title="Route Health" tone="deep" />
              <div className="flex items-center gap-2">
                <Chip label={`Active ${routeCounts.active}`} tone="good" />
                <Chip label={`Disrupted ${routeCounts.disrupted}`} tone="warn" pulse={routeCounts.disrupted > 0} />
                <Chip label={`Blocked ${routeCounts.blocked}`} tone="danger" pulse={routeCounts.blocked > 0} />
              </div>
            </div>
            <button
              onClick={() => setModalOpen(true)}
              className="btn-action px-3 py-1 text-[10px] uppercase tracking-[0.2em] border border-deep/40 text-deep"
            >
              Dispatch Shipment
            </button>
          </div>
        </CollapsibleModule>

        <CollapsibleModule
          id="deep-shipments"
          title="Shipments"
          tone="deep"
          isOpen={sections.shipments}
          onToggle={() => toggleSection('shipments')}
          summary={`${state.logistics.shipments.length} in transit`}
        >
          <div className="space-y-2">
            {state.logistics.shipments.length === 0 ? (
              <div className="glass-surface glass-strong glass-tone-deep glass-elev-low p-3 text-xs font-mono text-text-secondary">
                No active shipments.
              </div>
            ) : (
              state.logistics.shipments.map(shipment => {
                const progress =
                  shipment.totalDays === 0 ? 0 : 1 - shipment.daysRemaining / shipment.totalDays;
                return (
                  <div key={shipment.id} className="glass-surface glass-strong glass-tone-deep glass-elev-low p-3 space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                      <span className="text-text-primary">Shipment #{shipment.id}</span>
                      <Chip
                        label={
                          shipment.interdicted
                            ? `INTERDICTED (-${Math.round(shipment.interdictionLossPct * 100)}%)`
                            : 'CLEAR'
                        }
                        tone={shipment.interdicted ? 'danger' : 'core'}
                        size="sm"
                      />
                    </div>
                    <div className="text-xs font-mono text-text-secondary">
                      {shipment.origin} → {shipment.destination} • {shipment.daysRemaining}/{shipment.totalDays}D remaining
                    </div>
                    <InlineProgress value={progress} tone="deep" />
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 text-xs font-mono text-text-secondary">
                      <div>
                        Supplies A/F/M: {shipment.supplies.ammo}/{shipment.supplies.fuel}/{shipment.supplies.medSpares}
                      </div>
                      <div>
                        Units I/W/S: {shipment.units.infantry}/{shipment.units.walkers}/{shipment.units.support}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </CollapsibleModule>

        <CollapsibleModule
          id="deep-orders"
          title="Orders"
          tone="deep"
          isOpen={sections.orders}
          onToggle={() => toggleSection('orders')}
          summary={`${state.logistics.activeOrders.length} active logistics orders`}
        >
          <div className="space-y-2">
            {state.logistics.activeOrders.length === 0 ? (
              <div className="glass-surface glass-strong glass-tone-deep glass-elev-low p-3 text-xs font-mono text-text-secondary">
                No active orders.
              </div>
            ) : (
              state.logistics.activeOrders.map(order => (
                <div key={order.orderId} className="glass-surface glass-strong glass-tone-deep glass-elev-low p-3 space-y-2 text-xs font-mono">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-text-primary">Order {order.orderId}</span>
                    <span className="text-text-secondary uppercase tracking-[0.1em]">{order.status}</span>
                  </div>
                  <div className="text-text-secondary">
                    Route: {order.origin} → {order.finalDestination}
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-2 text-text-secondary">
                    <div>Carrier: {order.carrierId ?? '—'}</div>
                    <div>Current: {order.currentLocation}</div>
                    <div>Leg: {order.inTransitLeg ? `${order.inTransitLeg[0]}→${order.inTransitLeg[1]}` : '—'}</div>
                  </div>
                  <div className="text-text-secondary">Blocked Reason: {order.blockedReason ?? '—'}</div>
                </div>
              ))
            )}
          </div>
        </CollapsibleModule>

        <CollapsibleModule
          id="deep-fleet"
          title="Fleet"
          tone="deep"
          isOpen={sections.fleet}
          onToggle={() => toggleSection('fleet')}
          summary={`${state.logistics.ships.length} cargo ships`}
        >
          <div className="space-y-2">
            {state.logistics.ships.length === 0 ? (
              <div className="glass-surface glass-strong glass-tone-deep glass-elev-low p-3 text-xs font-mono text-text-secondary">
                No cargo ships available.
              </div>
            ) : (
              state.logistics.ships.map(ship => (
                <div key={ship.id} className="glass-surface glass-strong glass-tone-deep glass-elev-low p-3 text-xs font-mono">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-text-primary">{ship.name}</span>
                    <span className="text-text-secondary uppercase tracking-[0.1em]">{ship.state}</span>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-2 text-text-secondary mt-2">
                    <div>Location: {ship.location}</div>
                    <div>Destination: {ship.destination ?? '—'}</div>
                    <div>ETA: {ship.daysRemaining}/{ship.totalDays}D</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CollapsibleModule>

        <CollapsibleModule
          id="deep-transit-log"
          title="Transit Log"
          tone="deep"
          isOpen={sections.transitLog}
          onToggle={() => toggleSection('transitLog')}
          summary={`${Math.min(8, state.logistics.transitLog.length)} recent events`}
        >
          <div className="space-y-2">
            {state.logistics.transitLog.length === 0 ? (
              <div className="glass-surface glass-strong glass-tone-deep glass-elev-low p-3 text-xs font-mono text-text-secondary">
                Transit log is empty.
              </div>
            ) : (
              state.logistics.transitLog
                .slice(-8)
                .reverse()
                .map((entry, idx) => (
                  <div
                    key={`${entry.day}-${idx}`}
                    className="glass-surface glass-strong glass-tone-deep glass-elev-low p-3 text-xs font-mono"
                  >
                    <div className="flex flex-wrap items-center gap-3 text-text-secondary">
                      <span>Day {entry.day}</span>
                      <span className="uppercase tracking-[0.1em]">{entry.eventType}</span>
                    </div>
                    <div className="text-text-primary mt-1">{entry.message}</div>
                  </div>
                ))
            )}
          </div>
        </CollapsibleModule>
      </div>

      {modalOpen && (
        <DispatchModal
          payload={payload}
          origins={origins}
          destinations={destinations}
          onClose={() => setModalOpen(false)}
          onChange={setPayload}
          onSubmit={handleDispatch}
          canDispatch={Boolean(canDispatch)}
        />
      )}
    </div>
  );
}

function DispatchModal({
  payload,
  origins,
  destinations,
  onClose,
  onChange,
  onSubmit,
  canDispatch,
}: {
  payload: DispatchPayload;
  origins: string[];
  destinations: string[];
  onClose: () => void;
  onChange: (payload: DispatchPayload) => void;
  onSubmit: () => void;
  canDispatch: boolean;
}) {
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      <div className="modal-overlay absolute inset-0 bg-space/70" onClick={onClose} />
      <GlassSurface
        tone="deep"
        elevation="high"
        blur
        highlight
        className="modal-content relative w-full max-w-lg glass-strong"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-deep/20">
          <div className="text-deep font-bold tracking-[0.3em] text-xs uppercase">Dispatch Shipment</div>
          <button onClick={onClose} className="text-deep/70 hover:text-deep">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <label className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
              Origin
              <select
                className="mt-2 w-full glass-surface glass-strong glass-tone-deep p-2 text-text-primary font-mono"
                value={payload.origin}
                onChange={e =>
                  onChange({
                    ...payload,
                    origin: e.target.value,
                    destination: '',
                  })
                }
              >
                <option value="">Select origin</option>
                {origins.map(origin => (
                  <option key={origin} value={origin}>
                    {origin}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
              Destination
              <select
                className="mt-2 w-full glass-surface glass-strong glass-tone-deep p-2 text-text-primary font-mono"
                value={payload.destination}
                onChange={e => onChange({ ...payload, destination: e.target.value })}
                disabled={!payload.origin}
              >
                <option value="">Select destination</option>
                {destinations.map(destination => (
                  <option key={destination} value={destination}>
                    {destination}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {(['ammo', 'fuel', 'medSpares'] as const).map(key => (
              <label key={key} className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                {key === 'medSpares' ? 'Med+Spares' : key}
                <input
                  type="number"
                  min={0}
                  value={payload.supplies[key]}
                  onChange={e =>
                    onChange({
                      ...payload,
                      supplies: { ...payload.supplies, [key]: Number(e.target.value) },
                    })
                  }
                  className="mt-2 w-full glass-surface glass-strong glass-tone-deep p-2 text-text-primary font-mono"
                />
              </label>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-3">
            {(['infantry', 'walkers', 'support'] as const).map(key => (
              <label key={key} className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
                {key}
                <input
                  type="number"
                  min={0}
                  value={payload.units[key]}
                  onChange={e =>
                    onChange({
                      ...payload,
                      units: { ...payload.units, [key]: Number(e.target.value) },
                    })
                  }
                  className="mt-2 w-full glass-surface glass-strong glass-tone-deep p-2 text-text-primary font-mono"
                />
              </label>
            ))}
          </div>
          <button
            onClick={onSubmit}
            disabled={!canDispatch}
            className={`w-full py-3 font-bold tracking-[0.2em] ${
              canDispatch ? 'bg-deep text-space' : 'bg-white/5 text-white/30 cursor-not-allowed'
            }`}
          >
            DISPATCH
          </button>
        </div>
      </GlassSurface>
    </div>
  );
}
