"use client";

import { useCallback } from "react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { invalidateApiCache, renameWorkspace } from "@/lib/api";
import { getActionErrorCopy } from "@/lib/dashboard-formatters";
import type { Workspace } from "@/types/api";

type ShowToast = (title: string, message: string, tone?: "success" | "error" | "info", dedupeKey?: string) => void;

type UseWorkspaceRenameActionOptions = {
  applyWorkspaceSummary: (summary?: Partial<Workspace> | null) => void;
  mergeWorkspaceRecord: (record?: Workspace | null) => void;
  renamingWorkspace: Workspace | null;
  setRenameError: Dispatch<SetStateAction<string | null>>;
  setRenameSubmitting: Dispatch<SetStateAction<boolean>>;
  setRenamingWorkspace: Dispatch<SetStateAction<Workspace | null>>;
  showToast: ShowToast;
  triggerPostActionRefreshRef: MutableRefObject<
    ((orgId?: string, options?: { immediate?: boolean; includeDetails?: boolean }) => Promise<void>) | null
  >;
};

export function useWorkspaceRenameAction({
  applyWorkspaceSummary,
  mergeWorkspaceRecord,
  renamingWorkspace,
  setRenameError,
  setRenameSubmitting,
  setRenamingWorkspace,
  showToast,
  triggerPostActionRefreshRef,
}: UseWorkspaceRenameActionOptions) {
  const handleRenameWorkspace = useCallback(async (nextName: string) => {
    if (!renamingWorkspace) {
      return;
    }

    setRenameSubmitting(true);
    setRenameError(null);

    try {
      const result = await renameWorkspace(renamingWorkspace.org_id, nextName);
      applyWorkspaceSummary(result.updated_summary);
      if (result.updated_summary) {
        mergeWorkspaceRecord(result.updated_summary);
      }
      invalidateApiCache();
      void triggerPostActionRefreshRef.current?.(renamingWorkspace.org_id, {
        immediate: true,
        includeDetails: result.refresh_hint?.include_details ?? false,
      });
      setRenamingWorkspace(null);
    } catch (error) {
      const message = getActionErrorCopy("rename_workspace", error);
      setRenameError(message);
      showToast("Không thể đổi tên workspace", message, "error");
    } finally {
      setRenameSubmitting(false);
    }
  }, [
    applyWorkspaceSummary,
    mergeWorkspaceRecord,
    renamingWorkspace,
    setRenameError,
    setRenameSubmitting,
    setRenamingWorkspace,
    showToast,
    triggerPostActionRefreshRef,
  ]);

  return { handleRenameWorkspace };
}
