import { useMemo, useState } from 'react';
import type { ApiResponse, GameStateResponse } from '../../api/types';
import { postDispatchShipment } from '../../api/client';
import { Chip } from './ui/Chip';
import { InlineProgress } from './ui/InlineProgress';
import { KpiTile } from './ui/KpiTile';
import { SectionHeader } from './ui/SectionHeader';

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

export function DeepSpaceBar({ state, onActionResult }: DeepSpaceBarProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [payload, setPayload] = useState<DispatchPayload>({
    origin: '',
    destination: '',
    supplies: { ammo: 0, fuel: 0, medSpares: 0 },
    units: { infantry: 0, walkers: 0, support: 0 },
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
    return Array.from(
      new Set(
        state.logistics.routes
          .filter(route => route.origin === payload.origin)
          .map(route => route.destination)
      )
    );
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

  const handleDispatch = async () => {
    if (!canDispatch) return;
    const resp = await postDispatchShipment(payload);
    onActionResult(resp);
    setModalOpen(false);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <KpiTile label="Active Orders" value={state.logistics.activeOrders.length} tone="neutral" />
        <KpiTile label="In-Transit Shipments" value={state.logistics.shipments.length} tone="neutral" />
        <KpiTile label="Cargo Ships" value={state.logistics.ships.length} tone="neutral" />
        <KpiTile label="Route Health" value={routeHealth.toUpperCase()} tone="neutral" />
      </div>

      <div className="flex items-center justify-between">
        <SectionHeader title="Route Health" tone="deep" />
        <div className="flex items-center gap-2">
          <Chip label={`Active ${routeCounts.active}`} tone="good" />
          <Chip label={`Disrupted ${routeCounts.disrupted}`} tone="warn" pulse={routeCounts.disrupted > 0} />
          <Chip label={`Blocked ${routeCounts.blocked}`} tone="danger" pulse={routeCounts.blocked > 0} />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <SectionHeader title="Transit Control" tone="deep" />
        <button
          onClick={() => setModalOpen(true)}
          className="btn-action px-3 py-1 text-[10px] uppercase tracking-[0.2em] border border-deep/40 text-deep"
        >
          Dispatch Shipment
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="nodebar-table space-y-2">
          <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
            Shipments
          </div>
          <div className="table-compact">
            <div className="table-header">
              <span>ID</span>
              <span>Origin</span>
              <span>Destination</span>
              <span>Progress</span>
              <span>Risk</span>
              <span>Cargo</span>
            </div>
            {state.logistics.shipments.map(shipment => {
              const progress =
                shipment.totalDays === 0 ? 0 : 1 - shipment.daysRemaining / shipment.totalDays;
              return (
                <div className="table-row" key={shipment.id}>
                  <span>{shipment.id}</span>
                  <span>{shipment.origin}</span>
                  <span>{shipment.destination}</span>
                  <InlineProgress value={progress} tone="deep" />
                  <span>
                    <Chip
                      label={
                        shipment.interdicted
                          ? `INTERDICTED (-${Math.round(shipment.interdictionLossPct * 100)}%)`
                          : 'CLEAR'
                      }
                      tone={shipment.interdicted ? 'danger' : 'core'}
                      size="sm"
                    />
                  </span>
                  <span>
                    A/F/M {shipment.supplies.ammo}/{shipment.supplies.fuel}/{shipment.supplies.medSpares} •
                    I/W/S {shipment.units.infantry}/{shipment.units.walkers}/{shipment.units.support}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="nodebar-table space-y-2">
          <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
            Cargo Ships
          </div>
          <div className="table-compact table-cols-5">
            <div className="table-header">
              <span>Name</span>
              <span>Location</span>
              <span>State</span>
              <span>Destination</span>
              <span>ETA</span>
            </div>
            {state.logistics.ships.map(ship => (
              <div className="table-row" key={ship.id}>
                <span>{ship.name}</span>
                <span>{ship.location}</span>
                <span>{ship.state}</span>
                <span>{ship.destination ?? '—'}</span>
                <span>{ship.daysRemaining}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="nodebar-table space-y-2">
          <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
            Active Orders
          </div>
          <div className="table-compact table-cols-5">
            <div className="table-header">
              <span>Order</span>
              <span>Route</span>
              <span>Status</span>
              <span>Carrier</span>
              <span>Leg</span>
            </div>
            {state.logistics.activeOrders.map(order => (
              <div className="table-row" key={order.orderId}>
                <span>{order.orderId}</span>
                <span>
                  {order.origin} → {order.finalDestination}
                </span>
                <span>{order.status}</span>
                <span>{order.carrierId ?? '—'}</span>
                <span>{order.inTransitLeg ? `${order.inTransitLeg[0]}→${order.inTransitLeg[1]}` : '—'}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="nodebar-table space-y-2">
          <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary font-mono">
            Transit Log (Last 8)
          </div>
          <div className="table-compact table-cols-3">
            <div className="table-header">
              <span>Day</span>
              <span>Event</span>
              <span>Message</span>
            </div>
            {state.logistics.transitLog
              .slice(-8)
              .reverse()
              .map((entry, idx) => (
              <div className="table-row" key={`${entry.day}-${idx}`}>
                <span>{entry.day}</span>
                <span>{entry.eventType}</span>
                <span>{entry.message}</span>
              </div>
            ))}
          </div>
        </div>
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
      <div className="modal-overlay absolute inset-0 bg-space/60 backdrop-blur-sm" onClick={onClose} />
      <div className="modal-content relative w-full max-w-lg border border-deep/40 bg-space shadow-[0_0_40px_rgba(255,184,0,0.15)]">
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
                className="mt-2 w-full bg-space border border-deep/30 p-2 text-text-primary font-mono"
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
                className="mt-2 w-full bg-space border border-deep/30 p-2 text-text-primary font-mono"
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
                  className="mt-2 w-full bg-space border border-deep/30 p-2 text-text-primary font-mono"
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
                  className="mt-2 w-full bg-space border border-deep/30 p-2 text-text-primary font-mono"
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
      </div>
    </div>
  );
}
