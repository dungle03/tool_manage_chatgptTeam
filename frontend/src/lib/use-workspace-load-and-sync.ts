"use client";

import { useCallback, useRef } from "react";
import { getWorkspaceDetails, syncWorkspace } from "@/lib/api";
import { getActionErrorCopy } from "@/lib/dashboard-formatters";
import { mergeInviteLists } from "@/lib/workspace-state";
import { DEFAULT_WS_STATE, type UpdateWorkspaceState, type WorkspaceState } from "@/lib/workspace-dashboard-state";
import type { Workspace } from "@/types/api";

type ShowToast = (title: string, message: string, tone?: "success" | "error" | "info", dedupeKey?: string) => void;

type UseWorkspaceLoadAndSyncOptions = {
  applyWorkspaceSummary: (summary?: Partial<Workspace> | null) => void;
  showToast: ShowToast;
  triggerPostActionRefresh: (
    orgId?: string,
    options?: { immediate?: boolean; includeDetails?: boolean }
  ) => Promise<void>;
  updateWsState: UpdateWorkspaceState;
  wsStatesRef: React.MutableRefObject<Record<string, WorkspaceState>>;
};

export function useWorkspaceLoadAndSync({
  applyWorkspaceSummary,
  showToast,
  triggerPostActionRefresh,
  updateWsState,
  wsStatesRef,
}: UseWorkspaceLoadAndSyncOptions) {
  const inflightMemberLoads = useRef(new Map<string, Promise<void>>());

  const loadMembers = useCallback(async (orgId: string) => {
    const existingRequest = inflightMemberLoads.current.get(orgId);
    if (existingRequest) {
      return existingRequest;
    }

    const request = (async () => {
      updateWsState(orgId, { syncing: true });

      try {
        const details = await getWorkspaceDetails(orgId, { forceFresh: true });
        updateWsState(orgId, {
          syncing: false,
          members: details.members,
          loadedMembers: true,
          invites: mergeInviteLists(
            wsStatesRef.current[orgId]?.invites ?? [],
            details.invites,
          ),
        });
      } catch (error) {
        updateWsState(orgId, { syncing: false });
        showToast(
          "Không thể tải chi tiết workspace",
          `Workspace ${orgId}: ${getActionErrorCopy("sync", error)}`,
          "error"
        );
      }

      inflightMemberLoads.current.delete(orgId);
    })().finally(() => {
      updateWsState(orgId, { syncing: false });
      inflightMemberLoads.current.delete(orgId);
    });

    inflightMemberLoads.current.set(orgId, request);
    return request;
  }, [showToast, updateWsState, wsStatesRef]);

  const handleSync = useCallback(async (orgId: string) => {
    updateWsState(orgId, { syncing: true });
    try {
      const result = await syncWorkspace(orgId);
      applyWorkspaceSummary(result.updated_summary);

      if (result.already_in_progress) {
        void triggerPostActionRefresh(orgId, {
          includeDetails: result.refresh_hint?.include_details ?? true,
        });
        return;
      }

      const state = wsStatesRef.current[orgId] ?? DEFAULT_WS_STATE;

      if (state.loadedMembers) {
        void triggerPostActionRefresh(orgId, {
          includeDetails: result.refresh_hint?.include_details ?? true,
        });
      } else {
        await loadMembers(orgId);
      }
    } catch (error) {
      showToast(
        "Sync thất bại",
        getActionErrorCopy("sync", error),
        "error"
      );
      updateWsState(orgId, { syncing: false });
    }
  }, [applyWorkspaceSummary, loadMembers, showToast, triggerPostActionRefresh, updateWsState, wsStatesRef]);

  return {
    handleSync,
    loadMembers,
  };
}
