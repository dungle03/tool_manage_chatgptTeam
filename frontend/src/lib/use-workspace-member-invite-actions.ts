"use client";

import { useCallback } from "react";
import type { MutableRefObject } from "react";
import { cancelInvite, kickMember, resendInvite } from "@/lib/api";
import { getActionErrorCopy } from "@/lib/dashboard-formatters";
import { removeInvite, removeMember, replaceInvite } from "@/lib/workspace-state";
import type { UpdateWorkspaceState, WorkspaceState } from "@/lib/workspace-dashboard-state";
import type { Workspace } from "@/types/api";

type ShowToast = (title: string, message: string, tone?: "success" | "error" | "info", dedupeKey?: string) => void;

type UseWorkspaceMemberInviteActionsOptions = {
  applyWorkspaceSummary: (summary?: Partial<Workspace> | null) => void;
  showToast: ShowToast;
  triggerPostActionRefresh: (
    orgId?: string,
    options?: { immediate?: boolean; includeDetails?: boolean }
  ) => Promise<void>;
  updateWsState: UpdateWorkspaceState;
  wsStatesRef: MutableRefObject<Record<string, WorkspaceState>>;
};

export function useWorkspaceMemberInviteActions({
  applyWorkspaceSummary,
  showToast,
  triggerPostActionRefresh,
  updateWsState,
  wsStatesRef,
}: UseWorkspaceMemberInviteActionsOptions) {
  const handleKick = useCallback(async (orgId: string, memberId: number) => {
    updateWsState(orgId, (current) => ({
      busyMemberIds: [...current.busyMemberIds, memberId],
    }));

    try {
      const result = await kickMember({ org_id: orgId, member_id: memberId });
      const removedMemberId = result.member_id ?? memberId;
      updateWsState(orgId, (current) => ({
        members: removeMember(current.members, removedMemberId),
      }));
      applyWorkspaceSummary(result.updated_summary);
      void triggerPostActionRefresh(orgId, {
        includeDetails: result.refresh_hint?.include_details ?? true,
      });
    } catch (error) {
      showToast(
        "Không thể xóa thành viên",
        getActionErrorCopy("kick", error),
        "error"
      );
    } finally {
      updateWsState(orgId, (current) => ({
        busyMemberIds: current.busyMemberIds.filter((id) => id !== memberId),
      }));
    }
  }, [applyWorkspaceSummary, showToast, triggerPostActionRefresh, updateWsState]);

  const handleResendInvite = useCallback(async (orgId: string, inviteId: string, inviteEmail?: string) => {
    updateWsState(orgId, (current) => ({
      inviteActionState: {
        ...current.inviteActionState,
        [inviteId]: "resend",
      },
    }));

    try {
      const result = await resendInvite({ org_id: orgId, invite_id: inviteId, email: inviteEmail });
      if (result.updated_record) {
        const updatedInvite = result.updated_record;
        updateWsState(orgId, (current) => ({
          invites: replaceInvite(current.invites, inviteId, updatedInvite),
        }));
      }
      applyWorkspaceSummary(result.updated_summary);
      void triggerPostActionRefresh(orgId, {
        includeDetails: result.refresh_hint?.include_details ?? true,
      });
    } catch (error) {
      showToast(
        "Gửi lại thất bại",
        getActionErrorCopy("resend", error),
        "error"
      );
    } finally {
      updateWsState(orgId, (current) => {
        const next = { ...current.inviteActionState };
        delete next[inviteId];
        return { inviteActionState: next };
      });
    }
  }, [applyWorkspaceSummary, showToast, triggerPostActionRefresh, updateWsState]);

  const handleRevokeInvite = useCallback(async (orgId: string, inviteId: string) => {
    const previousInvites = wsStatesRef.current[orgId]?.invites ?? [];

    updateWsState(orgId, (current) => ({
      invites: removeInvite(current.invites, inviteId),
      inviteActionState: {
        ...current.inviteActionState,
        [inviteId]: "revoke",
      },
    }));

    try {
      const result = await cancelInvite({ org_id: orgId, invite_id: inviteId });
      applyWorkspaceSummary(result.updated_summary);
      void triggerPostActionRefresh(orgId, {
        includeDetails: result.refresh_hint?.include_details ?? true,
      });
    } catch (error) {
      updateWsState(orgId, {
        invites: previousInvites,
      });
      showToast(
        "Thu hồi thất bại",
        getActionErrorCopy("revoke", error),
        "error"
      );
    } finally {
      updateWsState(orgId, (current) => {
        const next = { ...current.inviteActionState };
        delete next[inviteId];
        return { inviteActionState: next };
      });
    }
  }, [applyWorkspaceSummary, showToast, triggerPostActionRefresh, updateWsState, wsStatesRef]);

  return {
    handleKick,
    handleResendInvite,
    handleRevokeInvite,
  };
}
