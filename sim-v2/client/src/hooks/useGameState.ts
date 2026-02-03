import { useState, useEffect, useCallback } from 'react';
import { getState } from '../api/client';
import type { ApiResponse, GameStateResponse } from '../api/types';

export function useGameState() {
  const [state, setState] = useState<GameStateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<{ message: string; kind?: ApiResponse['messageKind'] } | null>(
    null
  );

  const refresh = useCallback(async () => {
    try {
      const data = await getState();
      setState(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch game state:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  const applyApiResponse = useCallback((resp: ApiResponse) => {
    if (resp.state) {
      setState(resp.state);
    }
    if (resp.message) {
      setLastMessage({ message: resp.message, kind: resp.messageKind });
    }
  }, []);

  return { state, loading, error, refresh, applyApiResponse, lastMessage };
}
