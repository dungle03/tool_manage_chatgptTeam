"use client";

import { useCallback, useRef } from "react";
import { getWorkspaceMembers, listInvites, syncWorkspace } from "@/lib/api";
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
      const [membersResult, invitesResult] = await Promise.allSettled([
        getWorkspaceMembers(orgId, { forceFresh: true }),
        listInvites(orgId, { forceFresh: true }),
      ]);

      const nextPatch: Partial<WorkspaceState> = {
        syncing: false,
      };

      if (membersResult.status === "fulfilled") {
        nextPatch.members = membersResult.value;
        nextPatch.loadedMembers = true;
      }

      if (invitesResult.status === "fulfilled") {
        nextPatch.invites = mergeInviteLists(
          wsStatesRef.current[orgId]?.invites ?? [],
          invitesResult.value,
        );
      }

      updateWsState(orgId, nextPatch);

      if (membersResult.status === "rejected") {
        showToast(
          "Không thể tải danh sách thành viên",
          `Workspace ${orgId}: ${getActionErrorCopy("sync", membersResult.reason)}`,
          "error"
        );
      }

      if (invitesResult.status === "rejected") {
        showToast(
          "Không thể tải danh sách invite",
          `Workspace ${orgId}: ${getActionErrorCopy("sync", invitesResult.reason)}`,
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
