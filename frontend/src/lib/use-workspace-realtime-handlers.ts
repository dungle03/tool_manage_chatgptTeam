"use client";

import { useCallback, useRef } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { invalidateApiCache } from "@/lib/api";
import { DEFAULT_WS_STATE, type WorkspaceState } from "@/lib/workspace-dashboard-state";
import type { ToastTone } from "@/lib/use-dashboard-toasts";
import type { Workspace, WorkspaceEvent } from "@/types/api";

const RECOVERY_REFRESH_COOLDOWN_MS = 5_000;

type ShowToast = (title: string, message: string, tone?: ToastTone, dedupeKey?: string) => void;

type UseWorkspaceRealtimeHandlersOptions = {
  focusedWorkspaceId: string | null;
  handleTokenRefreshEvent: (event: WorkspaceEvent) => boolean;
  managedWorkspaceId: string | null;
  refreshGlobalUnauthorizedFindings: () => Promise<void> | void;
  refreshWorkspaceDetailsRef: MutableRefObject<((orgId: string) => Promise<void>) | null>;
  loadWorkspacesRef: MutableRefObject<
    ((options?: { silent?: boolean; forceFresh?: boolean }) => Promise<void>) | null
  >;
  scheduleWorkspaceDetailRefresh: (orgId: string) => void;
  scheduleWorkspaceListRefresh: () => void;
  setWorkspaces: Dispatch<SetStateAction<Workspace[]>>;
  showToastRef: MutableRefObject<ShowToast | null>;
  updateWsState: (
    orgId: string,
    patch: Partial<WorkspaceState> | ((current: WorkspaceState) => Partial<WorkspaceState>)
  ) => void;
  wsStatesRef: MutableRefObject<Record<string, WorkspaceState>>;
};

export function useWorkspaceRealtimeHandlers({
  focusedWorkspaceId,
  handleTokenRefreshEvent,
  managedWorkspaceId,
  refreshGlobalUnauthorizedFindings,
  refreshWorkspaceDetailsRef,
  loadWorkspacesRef,
  scheduleWorkspaceDetailRefresh,
  scheduleWorkspaceListRefresh,
  setWorkspaces,
  showToastRef,
  updateWsState,
  wsStatesRef,
}: UseWorkspaceRealtimeHandlersOptions) {
  const seenEventSequencesRef = useRef(new Set<number>());
  const lastRecoveryRefreshAtRef = useRef(0);

  const recoverDashboardState = useCallback(async () => {
    const now = Date.now();
    if (now - lastRecoveryRefreshAtRef.current < RECOVERY_REFRESH_COOLDOWN_MS) {
      return;
    }
    lastRecoveryRefreshAtRef.current = now;

    invalidateApiCache();
    await loadWorkspacesRef.current?.({ silent: true, forceFresh: true });

    const focusedOrgId = managedWorkspaceId ?? focusedWorkspaceId;
    if (!focusedOrgId) {
      return;
    }

    const state = wsStatesRef.current[focusedOrgId] ?? DEFAULT_WS_STATE;
    if (state.loadedMembers) {
      await refreshWorkspaceDetailsRef.current?.(focusedOrgId);
    }
  }, [focusedWorkspaceId, managedWorkspaceId, loadWorkspacesRef, refreshWorkspaceDetailsRef, wsStatesRef]);

  const handleWorkspaceEvent = useCallback((event: WorkspaceEvent) => {
    if (seenEventSequencesRef.current.has(event.sequence)) {
      return;
    }
    seenEventSequencesRef.current.add(event.sequence);
    if (seenEventSequencesRef.current.size > 100) {
      const recentSequences = Array.from(seenEventSequencesRef.current).slice(-50);
      seenEventSequencesRef.current = new Set(recentSequences);
    }

    if (event.type === "heartbeat") {
      return;
    }

    if (!event.org_id) {
      return;
    }

    if (event.type === "workspace_scheduled") {
      setWorkspaces((prev) =>
        prev.map((workspace) =>
          workspace.org_id === event.org_id
            ? {
                ...workspace,
                sync_reason: event.reason ?? workspace.sync_reason,
                next_sync_at:
                  event.next_sync_at !== undefined ? event.next_sync_at : workspace.next_sync_at,
                hot_until: event.hot_until !== undefined ? event.hot_until : workspace.hot_until,
                is_hot: event.is_hot ?? workspace.is_hot,
                sync_priority: event.priority ?? workspace.sync_priority,
              }
            : workspace
        )
      );
      return;
    }

    if (event.type === "sync_started") {
      updateWsState(event.org_id, { syncing: true });
      scheduleWorkspaceListRefresh();
      return;
    }

    if (event.type === "workspace_updated") {
      updateWsState(event.org_id, { syncing: false });
      scheduleWorkspaceListRefresh();
      scheduleWorkspaceDetailRefresh(event.org_id);
      setWorkspaces((prev) =>
        prev.map((workspace) =>
          workspace.org_id === event.org_id
            ? {
                ...workspace,
                sync_reason: event.reason ?? workspace.sync_reason,
                next_sync_at:
                  event.next_sync_at !== undefined ? event.next_sync_at : workspace.next_sync_at,
                hot_until: event.hot_until !== undefined ? event.hot_until : workspace.hot_until,
                is_hot: event.is_hot ?? workspace.is_hot,
                pending_invites:
                  event.summary?.pending_invites ?? workspace.pending_invites,
                member_count: event.summary?.member_count ?? workspace.member_count,
                unauthorized_active_count:
                  event.summary?.unauthorized_active_count ?? workspace.unauthorized_active_count,
                last_sync: event.summary?.last_sync ?? workspace.last_sync,
                status: event.summary?.status ?? workspace.status,
              }
            : workspace
        )
      );

      void refreshGlobalUnauthorizedFindings();

      if (event.trigger !== "auto") {
        showToastRef.current?.(
          "Realtime sync hoàn tất",
          `Workspace ${event.org_id} đã được cập nhật tự động.`,
          "success",
          `workspace-updated-${event.org_id}-${event.trigger ?? "manual"}`
        );
      }
      return;
    }

    if (handleTokenRefreshEvent(event)) {
      return;
    }

    if (event.type === "sync_failed") {
      updateWsState(event.org_id, { syncing: false });
      scheduleWorkspaceListRefresh();
      showToastRef.current?.(
        "Realtime sync lỗi",
        event.error?.message
          ? `Workspace ${event.org_id}: ${event.error.message}`
          : `Workspace ${event.org_id} đồng bộ thất bại.`,
        "error",
        `sync-failed-${event.org_id}`
      );
    }
  }, [
    handleTokenRefreshEvent,
    refreshGlobalUnauthorizedFindings,
    scheduleWorkspaceDetailRefresh,
    scheduleWorkspaceListRefresh,
    setWorkspaces,
    showToastRef,
    updateWsState,
  ]);

  const handleWorkspaceEventsReconnect = useCallback(() => {
    invalidateApiCache();
    void loadWorkspacesRef.current?.({ silent: true, forceFresh: true });
  }, [loadWorkspacesRef]);

  return {
    handleWorkspaceEvent,
    handleWorkspaceEventsReconnect,
    recoverDashboardState,
  };
}
