/**
 * API client for Schism Sim v2.
 * Live state will be wired in a follow-up: swap mock for getState() and map
 * response to MapState when /api/state is extended or /api/map exists.
 */

const API_BASE = '/api';

export async function getState(): Promise<unknown> {
  const res = await fetch(`${API_BASE}/state`, { credentials: 'include' });
  if (!res.ok) throw new Error(`getState failed: ${res.status}`);
  return res.json();
}
