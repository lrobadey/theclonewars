import type { Depot, Supplies, UnitStock } from "../api/types";

export function fmtInt(value: number): string {
  return Intl.NumberFormat("en-US").format(value);
}

export function fmtPct(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function sumSupplies(depots: Depot[]): Supplies {
  return depots.reduce(
    (acc, depot) => ({
      ammo: acc.ammo + depot.supplies.ammo,
      fuel: acc.fuel + depot.supplies.fuel,
      medSpares: acc.medSpares + depot.supplies.medSpares
    }),
    { ammo: 0, fuel: 0, medSpares: 0 }
  );
}

export function sumUnits(depots: Depot[]): UnitStock {
  return depots.reduce(
    (acc, depot) => ({
      infantry: acc.infantry + depot.units.infantry,
      walkers: acc.walkers + depot.units.walkers,
      support: acc.support + depot.units.support
    }),
    { infantry: 0, walkers: 0, support: 0 }
  );
}

export function labelize(id: string): string {
  return id
    .replace("contested_", "")
    .replace("new_system_", "")
    .replace(/_/g, " ")
    .toUpperCase();
}
