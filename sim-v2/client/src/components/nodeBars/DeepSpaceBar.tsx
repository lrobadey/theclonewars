import { useEffect, useMemo, useState } from 'react';
import type { ApiResponse, GameStateResponse } from '../../api/types';
import { postDispatchShipment } from '../../api/client';
import { Chip } from './ui/Chip';
import { InlineProgress } from './ui/InlineProgress';
import { KpiTile } from './ui/KpiTile';
import { SectionHeader } from './ui/SectionHeader';
import { GlassCard } from '../ui/GlassCard';

interface DeepSpaceBarProps {
  state: GameStateResponse;
  onActionResult: (resp: ApiResponse) => void;
}

type DispatchForm = {
  origin: string;
  destination: string;
  ammo: number;
  fuel: number;
  medSpares: number;
  infantry: number;
  walkers: number;
  support: number;
};

function routeStatus(risk: number) {
  if (risk > 0.6) return 'danger';
  if (risk > 0.3) return 'warn';
  return 'good';
}

function reachableDestinations(origin: string, routes: GameStateResponse['logistics']['routes']) {
  const graph = new Map<string, string[]>();
  routes.forEach(route => {
    const next = graph.get(route.origin) ?? [];
    next.push(route.destination);
    graph.set(route.origin, next);
  });

  const queue = [origin];
  const visited = new Set([origin]);
  const results: string[] = [];

  while (queue.length > 0) {
    const node = queue.shift();
    if (!node) continue;
    for (const next of graph.get(node) ?? []) {
      if (visited.has(next)) continue;
      visited.add(next);
      results.push(next);
      queue.push(next);
    }
  }

  return results;
}

export function DeepSpaceBar({ state, onActionResult }: DeepSpaceBarProps) {
  const depots = state.logistics.depots;
  const [form, setForm] = useState<DispatchForm>({
    origin: depots[0]?.id ?? '',
    destination: '',
    ammo: 100,
    fuel: 100,
    medSpares: 50,
    infantry: 100,
    walkers: 0,
    support: 0,
  });

  const destinations = useMemo(
    () => reachableDestinations(form.origin, state.logistics.routes),
    [form.origin, state.logistics.routes]
  );

  useEffect(() => {
    if (depots.length > 0 && !depots.some(depot => depot.id === form.origin)) {
      setForm(prev => ({ ...prev, origin: depots[0].id, destination: '' }));
      return;
    }
    if (destinations.length > 0 && !destinations.includes(form.destination)) {
      setForm(prev => ({ ...prev, destination: destinations[0] }));
    }
  }, [depots, destinations, form.destination, form.origin]);

  const activeShipments = useMemo(
    () => [...state.logistics.shipments].sort((a, b) => a.daysRemaining - b.daysRemaining),
    [state.logistics.shipments]
  );

  const routeRisk = useMemo(() => Math.max(0, ...state.logistics.routes.map(route => route.interdictionRisk)), [state.logistics.routes]);
  const cargoTotal = form.ammo + form.fuel + form.medSpares + form.infantry + form.walkers + form.support;

  const handleDispatch = async () => {
    if (!form.origin || !form.destination) return;
    const resp = await postDispatchShipment({
      origin: form.origin,
      destination: form.destination,
      supplies: {
        ammo: form.ammo,
        fuel: form.fuel,
        medSpares: form.medSpares,
      },
      units: {
        infantry: form.infantry,
        walkers: form.walkers,
        support: form.support,
      },
    });
    onActionResult(resp);
    if (resp.ok) {
      setForm(prev => ({ ...prev, ammo: 100, fuel: 100, medSpares: 50, infantry: 100, walkers: 0, support: 0 }));
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <KpiTile label="Routes" value={state.logistics.routes.length} tone="deep" />
        <KpiTile label="Shipments" value={activeShipments.length} tone="deep" />
        <KpiTile label="Transit Log" value={state.logistics.transitLog.length} tone="neutral" />
        <KpiTile label="Peak Risk" value={`${Math.round(routeRisk * 100)}%`} tone={routeStatus(routeRisk) === 'danger' ? 'neutral' : 'deep'} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <GlassCard tone="deep" elevation="low" className="p-4">
          <SectionHeader title="Dispatch Order" tone="deep" />
          <div className="mt-4 grid gap-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1">
                <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">Origin</div>
                <select
                  value={form.origin}
                  onChange={event => setForm(prev => ({ ...prev, origin: event.target.value, destination: '' }))}
                  className="w-full rounded border border-white/10 bg-space/60 px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-deep/60"
                >
                  {depots.map(depot => (
                    <option key={depot.id} value={depot.id}>
                      {depot.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">Destination</div>
                <select
                  value={form.destination}
                  onChange={event => setForm(prev => ({ ...prev, destination: event.target.value }))}
                  className="w-full rounded border border-white/10 bg-space/60 px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-deep/60"
                >
                  {destinations.length === 0 ? (
                    <option value="">No reachable destination</option>
                  ) : (
                    destinations.map(destination => (
                      <option key={destination} value={destination}>
                        {destination.replace(/_/g, ' ')}
                      </option>
                    ))
                  )}
                </select>
              </label>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {(['ammo', 'fuel', 'medSpares'] as const).map(key => (
                <label key={key} className="space-y-1">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">{key}</div>
                  <input
                    type="number"
                    min="0"
                    value={form[key]}
                    onChange={event => setForm(prev => ({ ...prev, [key]: Math.max(0, Number(event.target.value) || 0) }))}
                    className="w-full rounded border border-white/10 bg-space/60 px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-deep/60"
                  />
                </label>
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {(['infantry', 'walkers', 'support'] as const).map(key => (
                <label key={key} className="space-y-1">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">{key}</div>
                  <input
                    type="number"
                    min="0"
                    value={form[key]}
                    onChange={event => setForm(prev => ({ ...prev, [key]: Math.max(0, Number(event.target.value) || 0) }))}
                    className="w-full rounded border border-white/10 bg-space/60 px-3 py-2 font-mono text-sm text-text-primary outline-none focus:border-deep/60"
                  />
                </label>
              ))}
            </div>

            <button
              type="button"
              onClick={handleDispatch}
              disabled={!form.origin || !form.destination || cargoTotal <= 0}
              className="btn-action rounded border border-deep/30 px-4 py-2 text-[10px] uppercase tracking-[0.22em] text-deep disabled:cursor-not-allowed disabled:border-white/10 disabled:text-text-secondary"
            >
              Dispatch Shipment
            </button>
          </div>
        </GlassCard>

        <GlassCard tone="deep" elevation="low" className="p-4">
          <SectionHeader title="Route & Transit" tone="deep" />
          <div className="mt-4 space-y-3">
            {state.logistics.routes.map(route => (
              <div key={`${route.origin}-${route.destination}`} className="space-y-2 rounded border border-white/10 bg-space/40 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm text-text-primary">
                    {route.origin.replace(/_/g, ' ')} → {route.destination.replace(/_/g, ' ')}
                  </div>
                  <Chip label={routeStatus(route.interdictionRisk)} tone={routeStatus(route.interdictionRisk)} />
                </div>
                <div className="flex flex-wrap gap-3 text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">
                  <span>{route.travelDays} day leg</span>
                  <span>{Math.round(route.interdictionRisk * 100)}% interdiction risk</span>
                </div>
                <InlineProgress value={1 - route.interdictionRisk} tone="deep" />
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
        <GlassCard tone="deep" elevation="low" className="p-4">
          <SectionHeader title="In Transit" tone="deep" />
          <div className="mt-4 space-y-3">
            {activeShipments.length === 0 ? (
              <div className="rounded border border-white/10 bg-white/5 px-3 py-4 text-sm text-text-secondary">
                No active shipments.
              </div>
            ) : (
              activeShipments.map(shipment => {
                const progress = shipment.totalDays === 0 ? 0 : 1 - shipment.daysRemaining / shipment.totalDays;
                return (
                  <div key={shipment.id} className="space-y-2 rounded border border-white/10 bg-space/40 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm text-text-primary">
                        {shipment.origin.replace(/_/g, ' ')} → {shipment.destination.replace(/_/g, ' ')}
                      </div>
                      <Chip
                        label={shipment.interdicted ? `LOSS ${Math.round(shipment.interdictionLossPct * 100)}%` : 'CLEAR'}
                        tone={shipment.interdicted ? 'danger' : 'deep'}
                      />
                    </div>
                    <InlineProgress value={progress} tone="deep" />
                    <div className="flex flex-wrap gap-3 text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">
                      <span>{shipment.daysRemaining}/{shipment.totalDays} days</span>
                      <span>A {shipment.supplies.ammo} F {shipment.supplies.fuel} M {shipment.supplies.medSpares}</span>
                      <span>I {shipment.units.infantry} W {shipment.units.walkers} S {shipment.units.support}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </GlassCard>

        <GlassCard tone="deep" elevation="low" className="p-4">
          <SectionHeader title="Transit Log" tone="deep" />
          <div className="mt-4 space-y-2">
            {state.logistics.transitLog.length === 0 ? (
              <div className="rounded border border-white/10 bg-white/5 px-3 py-4 text-sm text-text-secondary">
                No recent logistics events.
              </div>
            ) : (
              state.logistics.transitLog.slice(0, 6).map(entry => (
                <div key={`${entry.day}-${entry.eventType}-${entry.message}`} className="rounded border border-white/10 bg-space/40 p-3">
                  <div className="flex items-center justify-between gap-3 text-[10px] uppercase tracking-[0.18em] text-text-secondary font-mono">
                    <span>Day {entry.day}</span>
                    <span>{entry.eventType}</span>
                  </div>
                  <div className="mt-1 text-sm text-text-primary">{entry.message}</div>
                </div>
              ))
            )}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
