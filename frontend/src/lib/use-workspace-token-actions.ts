"use client";

import { useCallback } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { invalidateApiCache, refreshWorkspaceToken, updateWorkspaceToken } from "@/lib/api";
import { getActionErrorCopy, getErrorMessage } from "@/lib/dashboard-formatters";
import type { Workspace } from "@/types/api";

type ShowToast = (title: string, message: string, tone?: "success" | "error" | "info", dedupeKey?: string) => void;

type UseWorkspaceTokenActionsOptions = {
  applyWorkspaceSummary: (summary?: Partial<Workspace> | null) => void;
  mergeWorkspaceRecord: (record?: Workspace | null) => void;
  setTokenError: Dispatch<SetStateAction<string | null>>;
  setTokenSubmitting: Dispatch<SetStateAction<boolean>>;
  setTokenWorkspace: Dispatch<SetStateAction<Workspace | null>>;
  showToast: ShowToast;
  startTokenRefreshPolling: (workspace: Workspace) => void;
  stopTokenRefreshPolling: (orgId: string) => void;
  tokenWorkspace: Workspace | null;
  triggerPostActionRefreshRef: MutableRefObject<
    ((orgId?: string, options?: { immediate?: boolean; includeDetails?: boolean }) => Promise<void>) | null
  >;
};

export function useWorkspaceTokenActions({
  applyWorkspaceSummary,
  mergeWorkspaceRecord,
  setTokenError,
  setTokenSubmitting,
  setTokenWorkspace,
  showToast,
  startTokenRefreshPolling,
  stopTokenRefreshPolling,
  tokenWorkspace,
  triggerPostActionRefreshRef,
}: UseWorkspaceTokenActionsOptions) {
  const handleUpdateWorkspaceToken = useCallback(async (accessToken: string) => {
    if (!tokenWorkspace) {
      return;
    }

    setTokenSubmitting(true);
    setTokenError(null);

    try {
      const result = await updateWorkspaceToken(tokenWorkspace.org_id, accessToken);
      applyWorkspaceSummary(result.updated_summary);
      if (result.updated_summary) {
        mergeWorkspaceRecord(result.updated_summary);
      }
      invalidateApiCache();
      void triggerPostActionRefreshRef.current?.(tokenWorkspace.org_id, {
        immediate: true,
        includeDetails: result.refresh_hint?.include_details ?? false,
      });
      setTokenWorkspace(null);
      showToast("Đã lưu token thủ công", "Token mới đã được cập nhật cho workspace.", "success");
    } catch (error) {
      const message = getActionErrorCopy("sync", error);
      setTokenError(message);
      showToast("Không thể cập nhật token", message, "error");
    } finally {
      setTokenSubmitting(false);
    }
  }, [
    applyWorkspaceSummary,
    mergeWorkspaceRecord,
    setTokenError,
    setTokenSubmitting,
    setTokenWorkspace,
    showToast,
    tokenWorkspace,
    triggerPostActionRefreshRef,
  ]);

  const handleRefreshWorkspaceToken = useCallback(async (workspace: Workspace) => {
    setTokenSubmitting(true);
    setTokenError(null);

    try {
      const result = await refreshWorkspaceToken(workspace.org_id);
      applyWorkspaceSummary(result.updated_summary);
      if (result.updated_summary) {
        mergeWorkspaceRecord(result.updated_summary);
      }
      invalidateApiCache();
      void triggerPostActionRefreshRef.current?.(workspace.org_id, {
        immediate: true,
        includeDetails: result.refresh_hint?.include_details ?? true,
      });

      if (result.status === "success") {
        stopTokenRefreshPolling(workspace.org_id);
        showToast("Refresh token thành công", result.message, "success");
        return;
      }

      if (result.status === "partial_success") {
        stopTokenRefreshPolling(workspace.org_id);
        showToast("Refresh token thành công một phần", result.message, "info");
        return;
      }

      if (result.status === "accepted") {
        startTokenRefreshPolling(result.updated_summary ?? workspace);
        showToast(
          "Đang refresh token",
          `Đã gửi yêu cầu refresh cho workspace ${workspace.org_id}. Dashboard sẽ báo tiếp khi hoàn tất.`,
          "info",
          `workspace-token-refresh-started-${workspace.org_id}`
        );
        return;
      }

      if (result.status === "in_progress") {
        startTokenRefreshPolling(result.updated_summary ?? workspace);
        showToast(
          "Workspace đang được xử lý",
          `Workspace ${workspace.org_id} đang refresh token. Dashboard sẽ báo khi xong.`,
          "info",
          `workspace-token-refresh-progress-${workspace.org_id}`
        );
        return;
      }

      showToast("Refresh token", result.message, "info");
    } catch (error) {
      const message = getErrorMessage(error);
      setTokenError(message);
      setTokenWorkspace(workspace);
      showToast("Không thể refresh token", message, "error");
    } finally {
      setTokenSubmitting(false);
    }
  }, [
    applyWorkspaceSummary,
    mergeWorkspaceRecord,
    setTokenError,
    setTokenSubmitting,
    setTokenWorkspace,
    showToast,
    startTokenRefreshPolling,
    stopTokenRefreshPolling,
    triggerPostActionRefreshRef,
  ]);

  return { handleRefreshWorkspaceToken, handleUpdateWorkspaceToken };
}
