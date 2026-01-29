import { useState } from "react";
import type { Depot, LogisticsState } from "../api/types";
import PanelShell from "../components/PanelShell";
import { fmtInt, labelize } from "../utils/format";

const emptyPayload = {
  ammo: 0,
  fuel: 0,
  medSpares: 0,
  infantry: 0,
  walkers: 0,
  support: 0
};

export default function LogisticsPanel({
  logistics,
  onDispatch
}: {
  logistics: LogisticsState;
  onDispatch: (payload: Record<string, unknown>) => void;
}) {
  const [origin, setOrigin] = useState(logistics.depots[0]?.id ?? "");
  const [destination, setDestination] = useState(logistics.depots[logistics.depots.length - 1]?.id ?? "");
  const [payload, setPayload] = useState(emptyPayload);
  const [selectedDepot, setSelectedDepot] = useState<Depot | null>(null);

  const handleDispatch = () => {
    onDispatch({
      origin,
      destination,
      supplies: {
        ammo: payload.ammo,
        fuel: payload.fuel,
        medSpares: payload.medSpares
      },
      units: {
        infantry: payload.infantry,
        walkers: payload.walkers,
        support: payload.support
      }
    });
    setPayload(emptyPayload);
  };

  return (
    <PanelShell title="Logistics & Supply Chain" tone="tone-deep">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="space-y-4">
          <div className="panel panel-live p-4 space-y-2">
            <h3 className="text-base">Depot Inspection</h3>
            <div className="flex flex-wrap gap-2">
              {logistics.depots.map((depot) => (
                <button
                  key={depot.id}
                  className={`control-button ${selectedDepot?.id === depot.id ? "ring-2 ring-emerald-300" : ""}`}
                  onClick={() => setSelectedDepot(depot)}
                >
                  {labelize(depot.label)}
                </button>
              ))}
            </div>
            {selectedDepot ? (
              <div className="text-xs text-soft space-y-1">
                <p>Ammo {fmtInt(selectedDepot.supplies.ammo)} | Fuel {fmtInt(selectedDepot.supplies.fuel)}</p>
                <p>Med {fmtInt(selectedDepot.supplies.medSpares)} | Infantry {fmtInt(selectedDepot.units.infantry)}</p>
                <p>Walkers {fmtInt(selectedDepot.units.walkers)} | Support {fmtInt(selectedDepot.units.support)}</p>
              </div>
            ) : (
              <p className="text-xs text-soft">Select a depot to inspect inventory.</p>
            )}
          </div>
          <div className="panel panel-live p-4 space-y-2">
            <h3 className="text-base">Transit Log</h3>
            {logistics.transitLog.length === 0 && <p className="text-xs text-soft">No transit events yet.</p>}
            <div className="space-y-2 max-h-40 overflow-y-auto pr-2 text-xs">
              {logistics.transitLog.map((entry, idx) => (
                <div key={`${entry.day}-${idx}`}>
                  <p className="text-soft">Day {entry.day}: {entry.message}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="space-y-4">
          <div className="panel panel-live p-4 space-y-3">
            <h3 className="text-base">Dispatch Shipment</h3>
            <div className="grid grid-cols-2 gap-2">
              <label className="text-xs text-soft">Origin
                <select className="input-field w-full mt-1" value={origin} onChange={(e) => setOrigin(e.target.value)}>
                  {logistics.depots.map((depot) => (
                    <option key={depot.id} value={depot.id}>{labelize(depot.label)}</option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-soft">Destination
                <select
                  className="input-field w-full mt-1"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                >
                  {logistics.depots.map((depot) => (
                    <option key={depot.id} value={depot.id}>{labelize(depot.label)}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <label className="text-soft">Ammo
                <input
                  className="input-field w-full mt-1"
                  type="number"
                  min={0}
                  value={payload.ammo}
                  onChange={(e) => setPayload({ ...payload, ammo: Number(e.target.value) })}
                />
              </label>
              <label className="text-soft">Fuel
                <input
                  className="input-field w-full mt-1"
                  type="number"
                  min={0}
                  value={payload.fuel}
                  onChange={(e) => setPayload({ ...payload, fuel: Number(e.target.value) })}
                />
              </label>
              <label className="text-soft">Med
                <input
                  className="input-field w-full mt-1"
                  type="number"
                  min={0}
                  value={payload.medSpares}
                  onChange={(e) => setPayload({ ...payload, medSpares: Number(e.target.value) })}
                />
              </label>
              <label className="text-soft">Infantry
                <input
                  className="input-field w-full mt-1"
                  type="number"
                  min={0}
                  value={payload.infantry}
                  onChange={(e) => setPayload({ ...payload, infantry: Number(e.target.value) })}
                />
              </label>
              <label className="text-soft">Walkers
                <input
                  className="input-field w-full mt-1"
                  type="number"
                  min={0}
                  value={payload.walkers}
                  onChange={(e) => setPayload({ ...payload, walkers: Number(e.target.value) })}
                />
              </label>
              <label className="text-soft">Support
                <input
                  className="input-field w-full mt-1"
                  type="number"
                  min={0}
                  value={payload.support}
                  onChange={(e) => setPayload({ ...payload, support: Number(e.target.value) })}
                />
              </label>
            </div>
            <button className="control-button w-full" onClick={handleDispatch}>
              Dispatch Order
            </button>
          </div>
          <div className="panel panel-live p-4 space-y-2">
            <h3 className="text-base">Active Shipments</h3>
            {logistics.shipments.length === 0 && <p className="text-xs text-soft">No active shipments.</p>}
            <div className="space-y-2 text-xs max-h-40 overflow-y-auto pr-2">
              {logistics.shipments.map((ship) => (
                <div key={ship.id}>
                  <p className="text-soft">
                    #{ship.id} {labelize(ship.origin)} → {labelize(ship.destination)} ({ship.daysRemaining}/{ship.totalDays}d)
                  </p>
                  {ship.interdicted && (
                    <p className="text-alert">Interdicted (-{Math.round(ship.interdictionLossPct * 100)}%)</p>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="panel panel-live p-4 space-y-2">
            <h3 className="text-base">Fleet Status</h3>
            {logistics.ships.length === 0 && <p className="text-xs text-soft">No ships assigned.</p>}
            <div className="space-y-2 text-xs">
              {logistics.ships.map((ship) => (
                <p key={ship.id} className="text-soft">
                  {ship.name}: {labelize(ship.location)} ({ship.state.toUpperCase()})
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </PanelShell>
  );
}
