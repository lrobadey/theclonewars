import { useState, useEffect, useCallback } from 'react';
import { getState } from '../api/client';
import type { GameStateResponse } from '../api/types';

export function useGameState() {
  const [state, setState] = useState<GameStateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return { state, loading, error, refresh };
}
