import { useCallback, useEffect, useRef, useState } from 'react';
import { postAdvanceDay } from '../api/client';
import type { ApiResponse, GameStateResponse } from '../api/types';

type AutoAdvanceStatus = 'idle' | 'running' | 'paused' | 'complete' | 'error';

function pauseReason(state: GameStateResponse): string | null {
  if (state.lastAar) {
    return 'Paused: after-action report ready.';
  }
  if (!state.operation) {
    return 'Paused: no active operation.';
  }
  if (state.operation.pendingPhaseRecord) {
    return 'Paused: phase report requires acknowledgment.';
  }
  if (state.operation.awaitingDecision) {
    return 'Paused: phase decisions required.';
  }
  return null;
}

export function useGuidedAutoAdvance(
  state: GameStateResponse | null,
  onActionResult: (resp: ApiResponse) => void
) {
  const [status, setStatus] = useState<AutoAdvanceStatus>('idle');
  const [message, setMessage] = useState('Idle');
  const stateRef = useRef<GameStateResponse | null>(state);
  const stopRef = useRef(false);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const stop = useCallback(() => {
    stopRef.current = true;
    setStatus('paused');
    setMessage('Paused: operator stop requested.');
  }, []);

  const run = useCallback(
    async (maxTicks = 20) => {
      const initial = stateRef.current;
      if (!initial) {
        setStatus('error');
        setMessage('Error: no connected game state.');
        return;
      }

      stopRef.current = false;
      setStatus('running');
      setMessage('Running guided day advancement...');

      let current: GameStateResponse = initial;
      for (let idx = 0; idx < maxTicks; idx += 1) {
        if (stopRef.current) {
          return;
        }
        const reason = pauseReason(current);
        if (reason) {
          setStatus('paused');
          setMessage(reason);
          return;
        }

        setMessage(`Running: tick ${idx + 1}/${maxTicks}`);
        const resp = await postAdvanceDay();
        onActionResult(resp);

        if (!resp.ok || !resp.state) {
          setStatus('error');
          setMessage(resp.message ?? 'Error advancing day.');
          return;
        }

        current = resp.state;
        const postTickPause = pauseReason(current);
        if (postTickPause) {
          setStatus('paused');
          setMessage(postTickPause);
          return;
        }
      }

      setStatus('complete');
      setMessage(`Complete: reached max ticks (${maxTicks}).`);
    },
    [onActionResult]
  );

  return {
    status,
    message,
    running: status === 'running',
    run,
    stop,
  };
}
