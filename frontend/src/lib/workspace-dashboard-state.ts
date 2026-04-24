import type { Invite, Member } from "@/types/api";

export type WorkspaceState = {
  members: Member[];
  invites: Invite[];
  loadedMembers: boolean;
  syncing: boolean;
  busyMemberIds: number[];
  inviteActionState: Record<string, "resend" | "revoke">;
};

export const DEFAULT_WS_STATE: WorkspaceState = {
  members: [],
  invites: [],
  loadedMembers: false,
  syncing: false,
  busyMemberIds: [],
  inviteActionState: {},
};

export type UpdateWorkspaceState = (
  orgId: string,
  patch:
    | Partial<WorkspaceState>
    | ((current: WorkspaceState) => Partial<WorkspaceState>)
) => void;
