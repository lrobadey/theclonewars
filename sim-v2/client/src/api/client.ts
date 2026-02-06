/**
 * API client for Schism Sim v2.
 * Live state will be wired in a follow-up: swap mock for getState() and map
 * response to MapState when /api/state is extended or /api/map exists.
 */

import type { ApiResponse, CatalogResponse, GameStateResponse, PhaseDecisionRequest } from './types';

const API_BASE = '/api';

export async function getState(): Promise<GameStateResponse> {
  const res = await fetch(`${API_BASE}/state`, { credentials: 'include' });
  if (!res.ok) throw new Error(`getState failed: ${res.status}`);
  return res.json();
}

export async function getCatalog(): Promise<CatalogResponse> {
  const res = await fetch(`${API_BASE}/catalog`, { credentials: 'include' });
  if (!res.ok) throw new Error(`getCatalog failed: ${res.status}`);
  return res.json();
}

async function postJson<T>(path: string, payload?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: payload ? { 'Content-Type': 'application/json' } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export async function postAdvanceDay(): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/advance-day');
}

export async function postQueueProduction(
  jobType: 'ammo' | 'fuel' | 'med_spares' | 'walkers',
  quantity: number
): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/production', { jobType, quantity });
}

export async function postQueueBarracks(
  jobType: 'infantry' | 'support',
  quantity: number
): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/barracks', { jobType, quantity });
}

export async function postUpgradeFactory(): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/upgrade-factory');
}

export async function postUpgradeBarracks(): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/upgrade-barracks');
}

export async function postDispatchShipment(payload: {
  origin: string;
  destination: string;
  supplies: { ammo: number; fuel: number; medSpares: number };
  units: { infantry: number; walkers: number; support: number };
}): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/dispatch', payload);
}

export async function postStartOperation(payload: {
  target: string;
  opType: string;
}): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/operation/start', payload);
}

export async function postSubmitPhaseDecisions(payload: PhaseDecisionRequest): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/operation/decisions', payload);
}

export async function postAckPhase(): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/operation/ack-phase');
}

export async function postAckAar(): Promise<ApiResponse> {
  return postJson<ApiResponse>('/actions/ack-aar');
}
