"use client";

import { useCallback, useEffect, useRef } from "react";
import { buildWorkspaceEventsUrl, parseWorkspaceEvent } from "@/lib/api";
import type { WorkspaceEvent } from "@/types/api";

type UseWorkspaceEventsOptions = {
  onEvent: (event: WorkspaceEvent) => void;
  onReconnect: () => void;
};

const WORKSPACE_EVENT_TYPES = [
  "heartbeat",
  "workspace_scheduled",
  "sync_started",
  "workspace_updated",
  "workspace_token_refreshed",
  "workspace_token_refresh_failed",
  "sync_failed",
] as const;

export function useWorkspaceEvents({ onEvent, onReconnect }: UseWorkspaceEventsOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const onEventRef = useRef(onEvent);
  const onReconnectRef = useRef(onReconnect);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    onReconnectRef.current = onReconnect;
  }, [onReconnect]);

  const connectWorkspaceEvents = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(buildWorkspaceEventsUrl());
    eventSourceRef.current = eventSource;

    const onMessage = (message: MessageEvent<string>) => {
      try {
        const payload = parseWorkspaceEvent(message.data);
        reconnectAttemptsRef.current = 0;
        onEventRef.current(payload);
      } catch (error) {
        if (process.env.NODE_ENV !== "production") {
          console.warn("Ignoring malformed workspace event", error, message.data);
        }
      }
    };

    const onError = () => {
      eventSource.close();
      eventSourceRef.current = null;

      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }

      const attempt = Math.min(reconnectAttemptsRef.current + 1, 5);
      reconnectAttemptsRef.current = attempt;
      const delay = Math.min(1000 * 2 ** (attempt - 1), 15000);

      reconnectTimerRef.current = window.setTimeout(() => {
        connectWorkspaceEvents();
        onReconnectRef.current();
      }, delay);
    };

    eventSource.onmessage = onMessage;
    for (const eventType of WORKSPACE_EVENT_TYPES) {
      eventSource.addEventListener(eventType, onMessage as EventListener);
    }
    eventSource.onerror = onError;
  }, []);

  useEffect(() => {
    connectWorkspaceEvents();

    return () => {
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connectWorkspaceEvents]);
}
