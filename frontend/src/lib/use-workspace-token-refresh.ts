"use client";

import { useCallback, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";

import { getWorkspaces, invalidateApiCache } from "@/lib/api";
import type { Workspace, WorkspaceEvent } from "@/types/api";

const TOKEN_REFRESH_POLL_INTERVAL_MS = 2_500;
const TOKEN_REFRESH_POLL_DELAY_NOTICE_ATTEMPT = 12;
const TOKEN_REFRESH_POLL_MAX_ATTEMPTS = 48;

type ToastTone = "success" | "error" | "info";

type TokenRefreshPollState = {
  baselineExpiry: string | null | undefined;
  baselineRefreshAt: string | null | undefined;
  baselineError: string | null | undefined;
  baselineFailCount: number | null | undefined;
  attempts: number;
  timeoutNotified: boolean;
};

type TokenRefreshPollingResult =
  | { kind: "success"; message: string }
  | { kind: "failure"; message: string }
  | { kind: "continue" };

type UseWorkspaceTokenRefreshLifecycleOptions = {
  applyWorkspaceSummary: (summary?: Partial<Workspace> | null) => void;
  mergeWorkspaceRecord: (workspace: Workspace) => void;
  refreshWorkspaceList: (options?: { silent?: boolean; forceFresh?: boolean }) => Promise<void> | void;
  scheduleWorkspaceDetailRefresh: (orgId: string) => void;
  setWorkspaceSyncing: (orgId: string, syncing: boolean) => void;
  setWorkspaces: Dispatch<SetStateAction<Workspace[]>>;
  showToast: (title: string, message: string, tone?: ToastTone, dedupeKey?: string) => void;
};

function buildTokenRefreshSuccessMessage(orgId: string, summary?: Partial<Workspace> | null): string {
  const expiryCopy = formatAccessTokenRemainingTime(summary?.access_token_expires_at);
  return expiryCopy
    ? `Workspace ${orgId} đã cập nhật token mới. Hạn dùng còn khoảng ${expiryCopy}.`
    : `Workspace ${orgId} đã cập nhật token và thời hạn mới.`;
}

function createTokenRefreshPollState(workspace: Workspace): TokenRefreshPollState {
  return {
    baselineExpiry: workspace.access_token_expires_at,
    baselineRefreshAt: workspace.last_token_refresh_at,
    baselineError: workspace.last_token_refresh_error,
    baselineFailCount: workspace.token_refresh_fail_count,
    attempts: 0,
    timeoutNotified: false,
  };
}

function getTokenRefreshPollingResult(
  orgId: string,
  latestWorkspace: Workspace,
  state: TokenRefreshPollState
): TokenRefreshPollingResult {
  const refreshAtChanged = latestWorkspace.last_token_refresh_at !== state.baselineRefreshAt;
  const expiryChanged = latestWorkspace.access_token_expires_at !== state.baselineExpiry;
  const errorChanged = latestWorkspace.last_token_refresh_error !== state.baselineError;
  const failCountChanged = latestWorkspace.token_refresh_fail_count !== state.baselineFailCount;

  if (refreshAtChanged || expiryChanged) {
    return {
      kind: "success",
      message: buildTokenRefreshSuccessMessage(orgId, latestWorkspace),
    };
  }

  if ((errorChanged || failCountChanged) && latestWorkspace.last_token_refresh_error) {
    return {
      kind: "failure",
      message: `Workspace ${orgId}: ${latestWorkspace.last_token_refresh_error}`,
    };
  }

  return { kind: "continue" };
}

function advanceTokenRefreshPollState(state: TokenRefreshPollState) {
  const nextAttempts = state.attempts + 1;
  return {
    nextState: {
      ...state,
      attempts: nextAttempts,
      timeoutNotified:
        state.timeoutNotified || nextAttempts >= TOKEN_REFRESH_POLL_DELAY_NOTICE_ATTEMPT,
    },
    shouldNotifyDelay:
      nextAttempts >= TOKEN_REFRESH_POLL_DELAY_NOTICE_ATTEMPT && !state.timeoutNotified,
    hasReachedAttemptLimit: nextAttempts >= TOKEN_REFRESH_POLL_MAX_ATTEMPTS,
  };
}

function formatAccessTokenRemainingTime(timestamp?: string | null): string | null {
  if (!timestamp) return null;

  const target = new Date(timestamp).getTime();
  if (Number.isNaN(target)) return null;

  const diffSeconds = Math.max(Math.floor((target - Date.now()) / 1000), 0);
  const days = Math.floor(diffSeconds / 86400);
  const hours = Math.floor((diffSeconds % 86400) / 3600);
  const minutes = Math.floor((diffSeconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return "sắp hết hạn";
}

export function useWorkspaceTokenRefreshLifecycle({
  applyWorkspaceSummary,
  mergeWorkspaceRecord,
  refreshWorkspaceList,
  scheduleWorkspaceDetailRefresh,
  setWorkspaceSyncing,
  setWorkspaces,
  showToast,
}: UseWorkspaceTokenRefreshLifecycleOptions) {
  const tokenRefreshPollTimersRef = useRef(new Map<string, number>());
  const tokenRefreshPollStateRef = useRef(new Map<string, TokenRefreshPollState>());

  const stopTokenRefreshPolling = useCallback((orgId: string) => {
    const timerId = tokenRefreshPollTimersRef.current.get(orgId);
    if (timerId) {
      window.clearTimeout(timerId);
      tokenRefreshPollTimersRef.current.delete(orgId);
    }
    tokenRefreshPollStateRef.current.delete(orgId);
  }, []);

  const clearTokenRefreshPolling = useCallback(() => {
    for (const timerId of tokenRefreshPollTimersRef.current.values()) {
      window.clearTimeout(timerId);
    }
    tokenRefreshPollTimersRef.current.clear();
    tokenRefreshPollStateRef.current.clear();
  }, []);

  const startTokenRefreshPolling = useCallback((workspace: Workspace) => {
    stopTokenRefreshPolling(workspace.org_id);
    tokenRefreshPollStateRef.current.set(workspace.org_id, createTokenRefreshPollState(workspace));

    const poll = async () => {
      const state = tokenRefreshPollStateRef.current.get(workspace.org_id);
      if (!state) {
        return;
      }

      try {
        const latestWorkspaces = await getWorkspaces({ forceFresh: true });
        const latestWorkspace = latestWorkspaces.find((item) => item.org_id === workspace.org_id);
        if (!latestWorkspace) {
          stopTokenRefreshPolling(workspace.org_id);
          return;
        }

        setWorkspaces(latestWorkspaces);
        applyWorkspaceSummary(latestWorkspace);
        mergeWorkspaceRecord(latestWorkspace);

        const pollingResult = getTokenRefreshPollingResult(
          workspace.org_id,
          latestWorkspace,
          state
        );

        if (pollingResult.kind === "success") {
          stopTokenRefreshPolling(workspace.org_id);
          showToast(
            "Refresh token thành công",
            pollingResult.message,
            "success",
            `workspace-token-refreshed-${workspace.org_id}`
          );
          return;
        }

        if (pollingResult.kind === "failure") {
          stopTokenRefreshPolling(workspace.org_id);
          showToast(
            "Refresh token thất bại",
            pollingResult.message,
            "error",
            `workspace-token-refresh-failed-${workspace.org_id}`
          );
          return;
        }
      } catch {
        // Keep polling quietly; the SSE path may still arrive.
      }

      const nextState = tokenRefreshPollStateRef.current.get(workspace.org_id);
      if (!nextState) {
        return;
      }

      const pollingAdvance = advanceTokenRefreshPollState(nextState);
      tokenRefreshPollStateRef.current.set(workspace.org_id, pollingAdvance.nextState);

      if (pollingAdvance.shouldNotifyDelay) {
        showToast(
          "Refresh token đang xử lý lâu hơn dự kiến",
          `Workspace ${workspace.org_id} vẫn đang được theo dõi trong nền. Dashboard sẽ báo tiếp ngay khi refresh hoàn tất.`,
          "info",
          `workspace-token-refresh-timeout-${workspace.org_id}`
        );
      }

      if (pollingAdvance.hasReachedAttemptLimit) {
        stopTokenRefreshPolling(workspace.org_id);
        showToast(
          "Refresh token vẫn chưa hoàn tất",
          `Workspace ${workspace.org_id} đang mất nhiều thời gian hơn bình thường. Anh có thể tiếp tục chờ hoặc bấm refresh lại để kiểm tra.`,
          "info",
          `workspace-token-refresh-gave-up-${workspace.org_id}`
        );
        return;
      }

      const timerId = window.setTimeout(() => {
        void poll();
      }, TOKEN_REFRESH_POLL_INTERVAL_MS);
      tokenRefreshPollTimersRef.current.set(workspace.org_id, timerId);
    };

    const timerId = window.setTimeout(() => {
      void poll();
    }, TOKEN_REFRESH_POLL_INTERVAL_MS);
    tokenRefreshPollTimersRef.current.set(workspace.org_id, timerId);
  }, [applyWorkspaceSummary, mergeWorkspaceRecord, setWorkspaces, showToast, stopTokenRefreshPolling]);

  const handleTokenRefreshEvent = useCallback((event: WorkspaceEvent): boolean => {
    if (!event.org_id) {
      return false;
    }

    if (event.type === "workspace_token_refreshed") {
      stopTokenRefreshPolling(event.org_id);
      setWorkspaceSyncing(event.org_id, false);
      if (event.summary) {
        mergeWorkspaceRecord(event.summary as Workspace);
      } else {
        invalidateApiCache();
        void refreshWorkspaceList({ silent: true, forceFresh: true });
      }
      scheduleWorkspaceDetailRefresh(event.org_id);
      showToast(
        "Refresh token thành công",
        buildTokenRefreshSuccessMessage(event.org_id, event.summary),
        "success",
        `workspace-token-refreshed-${event.org_id}`
      );
      return true;
    }

    if (event.type === "workspace_token_refresh_failed") {
      stopTokenRefreshPolling(event.org_id);
      setWorkspaceSyncing(event.org_id, false);
      if (event.summary) {
        mergeWorkspaceRecord(event.summary as Workspace);
      } else {
        invalidateApiCache();
        void refreshWorkspaceList({ silent: true, forceFresh: true });
      }
      scheduleWorkspaceDetailRefresh(event.org_id);
      showToast(
        "Refresh token thất bại",
        event.error?.message
          ? `Workspace ${event.org_id}: ${event.error.message}`
          : `Workspace ${event.org_id} không thể cập nhật token.`,
        "error",
        `workspace-token-refresh-failed-${event.org_id}`
      );
      return true;
    }

    return false;
  }, [mergeWorkspaceRecord, refreshWorkspaceList, scheduleWorkspaceDetailRefresh, setWorkspaceSyncing, showToast, stopTokenRefreshPolling]);

  return {
    clearTokenRefreshPolling,
    handleTokenRefreshEvent,
    startTokenRefreshPolling,
    stopTokenRefreshPolling,
  };
}
