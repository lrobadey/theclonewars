import { useCallback, useEffect, useRef, useState } from "react";
import { getState, postAction } from "../api/client";
import type { ApiResponse, GameStateResponse } from "../api/types";

export type MessageEntry = {
  id: string;
  text: string;
  kind: "info" | "error" | "accent";
  timestamp: string;
};

export function useGameState() {
  const [state, setState] = useState<GameStateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageEntry[]>([]);
  const pollRef = useRef<number | null>(null);

  const pushMessage = useCallback((text: string, kind: "info" | "error" | "accent" = "info") => {
    const entry: MessageEntry = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      text,
      kind,
      timestamp: new Date().toLocaleTimeString()
    };
    setMessages((prev) => [entry, ...prev].slice(0, 8));
  }, []);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getState();
      setState(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load state.");
    } finally {
      setLoading(false);
    }
  }, []);

  const send = useCallback(
    async (path: string, payload?: Record<string, unknown>) => {
      try {
        const res = await postAction(path, payload);
        if (res.state) {
          setState(res.state);
        }
        if (res.message) {
          pushMessage(res.message, res.messageKind ?? "info");
        }
        return res;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Action failed.";
        pushMessage(message, "error");
        return { ok: false, message, messageKind: "error" } as ApiResponse;
      }
    },
    [pushMessage]
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    pollRef.current = window.setInterval(() => {
      refresh();
    }, 5000);
    return () => {
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
      }
    };
  }, [refresh]);

  return {
    state,
    loading,
    error,
    refresh,
    send,
    messages,
    pushMessage
  };
}
