import type { Invite, Member, Workspace } from "@/types/api";

export function parseDateValue(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }

  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

export function compareWorkspaceExpiry(a: Workspace, b: Workspace): number {
  const expiryA = parseDateValue(a.expires_at);
  const expiryB = parseDateValue(b.expires_at);

  if (expiryA === null && expiryB === null) {
    return a.name.localeCompare(b.name);
  }
  if (expiryA === null) {
    return 1;
  }
  if (expiryB === null) {
    return -1;
  }
  if (expiryA !== expiryB) {
    return expiryA - expiryB;
  }

  return a.name.localeCompare(b.name);
}

export function applyWorkspaceSummaryList(
  workspaces: Workspace[],
  summary?: Partial<Workspace> | null,
): Workspace[] {
  if (!summary?.org_id) {
    return workspaces;
  }

  const existingIndex = workspaces.findIndex(
    (workspace) => workspace.org_id === summary.org_id,
  );
  if (existingIndex === -1) {
    return workspaces;
  }

  return workspaces.map((workspace) =>
    workspace.org_id === summary.org_id ? { ...workspace, ...summary } : workspace,
  );
}

export function mergeWorkspaceRecordList(
  workspaces: Workspace[],
  record?: Workspace | null,
): Workspace[] {
  if (!record?.org_id) {
    return workspaces;
  }

  const existingIndex = workspaces.findIndex(
    (workspace) => workspace.org_id === record.org_id,
  );
  if (existingIndex === -1) {
    return [record, ...workspaces].sort(compareWorkspaceExpiry);
  }

  return workspaces
    .map((workspace) =>
      workspace.org_id === record.org_id ? { ...workspace, ...record } : workspace,
    )
    .sort(compareWorkspaceExpiry);
}

export function upsertInvite(invites: Invite[], invite: Invite): Invite[] {
  const withoutDuplicate = invites.filter(
    (item) => item.invite_id !== invite.invite_id && item.email !== invite.email,
  );
  return [invite, ...withoutDuplicate];
}

export function replaceInvite(invites: Invite[], inviteId: string, updatedInvite: Invite): Invite[] {
  return invites.map((invite) =>
    invite.invite_id === inviteId || invite.email === updatedInvite.email
      ? updatedInvite
      : invite,
  );
}

export function removeInvite(invites: Invite[], inviteId: string): Invite[] {
  return invites.filter((invite) => invite.invite_id !== inviteId);
}

export function removeMember(members: Member[], memberId: number): Member[] {
  return members.filter((member) => member.id !== memberId);
}
