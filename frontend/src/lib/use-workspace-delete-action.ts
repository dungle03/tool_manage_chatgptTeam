"use client";

import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";
import { deleteWorkspace } from "@/lib/api";
import { getActionErrorCopy } from "@/lib/dashboard-formatters";
import type { Workspace } from "@/types/api";
import type { WorkspaceState } from "@/lib/workspace-dashboard-state";

type ShowToast = (title: string, message: string, tone?: "success" | "error" | "info", dedupeKey?: string) => void;

type UseWorkspaceDeleteActionOptions = {
  deletingWs: Workspace | null;
  focusedWorkspaceId: string | null;
  setDeleting: Dispatch<SetStateAction<boolean>>;
  setDeletingWs: Dispatch<SetStateAction<Workspace | null>>;
  setFocusedWorkspaceId: Dispatch<SetStateAction<string | null>>;
  setWorkspaces: Dispatch<SetStateAction<Workspace[]>>;
  setWsStates: Dispatch<SetStateAction<Record<string, WorkspaceState>>>;
  showToast: ShowToast;
  triggerPostActionRefresh: (
    orgId?: string,
    options?: { immediate?: boolean; includeDetails?: boolean }
  ) => Promise<void>;
};

export function useWorkspaceDeleteAction({
  deletingWs,
  focusedWorkspaceId,
  setDeleting,
  setDeletingWs,
  setFocusedWorkspaceId,
  setWorkspaces,
  setWsStates,
  showToast,
  triggerPostActionRefresh,
}: UseWorkspaceDeleteActionOptions) {
  const handleConfirmDelete = useCallback(async () => {
    if (!deletingWs) return;

    setDeleting(true);
    try {
      const result = await deleteWorkspace(deletingWs.org_id);
      setWorkspaces((prev) =>
        prev.filter((workspace) => workspace.org_id !== (result.deleted_org_id ?? deletingWs.org_id))
      );
      setWsStates((prev) => {
        const next = { ...prev };
        delete next[deletingWs.org_id];
        return next;
      });
      if (focusedWorkspaceId === deletingWs.org_id) {
        setFocusedWorkspaceId(null);
      }
      void triggerPostActionRefresh(undefined, {
        includeDetails: result.refresh_hint?.include_details ?? false,
      });
      setDeletingWs(null);
    } catch (error) {
      showToast(
        "Không thể xóa workspace",
        getActionErrorCopy("delete_workspace", error),
        "error"
      );
    } finally {
      setDeleting(false);
    }
  }, [
    deletingWs,
    focusedWorkspaceId,
    setDeleting,
    setDeletingWs,
    setFocusedWorkspaceId,
    setWorkspaces,
    setWsStates,
    showToast,
    triggerPostActionRefresh,
  ]);

  return { handleConfirmDelete };
}
