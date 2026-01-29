import type { ApiResponse, GameStateResponse } from "./types";

async function fetchJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    },
    ...init
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function getState(): Promise<GameStateResponse> {
  return fetchJson<GameStateResponse>("/api/state");
}

export async function postAction<TPayload extends Record<string, unknown>>(
  path: string,
  payload?: TPayload
): Promise<ApiResponse> {
  return fetchJson<ApiResponse>(`/api${path}`, {
    method: "POST",
    body: JSON.stringify(payload ?? {})
  });
}
