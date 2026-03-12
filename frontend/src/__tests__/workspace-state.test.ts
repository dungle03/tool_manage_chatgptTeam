import { describe, expect, it } from "vitest";
import type { Invite, Member, Workspace } from "@/types/api";
import {
  applyWorkspaceSummaryList,
  mergeWorkspaceRecordList,
  removeInvite,
  removeMember,
  replaceInvite,
  upsertInvite,
} from "@/lib/workspace-state";

const baseWorkspace: Workspace = {
  id: 1,
  org_id: "org_001",
  account_id: "acc_001",
  name: "Team Alpha",
  status: "live",
  member_count: 2,
  member_limit: 10,
  pending_invites: 1,
  expires_at: null,
  last_sync: null,
  created_at: "2026-03-12T00:00:00+00:00",
  current_user_role: "owner",
  can_manage_members: true,
};

const inviteA: Invite = {
  id: 1,
  org_id: "org_001",
  email: "a@company.com",
  invite_id: "inv_a",
  status: "pending",
  created_at: "2026-03-12T00:00:00+00:00",
};

const inviteB: Invite = {
  id: 2,
  org_id: "org_001",
  email: "b@company.com",
  invite_id: "inv_b",
  status: "pending",
  created_at: "2026-03-12T00:00:00+00:00",
};

const memberA: Member = {
  id: 1,
  remote_id: "remote_1",
  name: "Member A",
  email: "member@company.com",
  role: "member",
  status: "active",
  invite_date: null,
  created_at: null,
  picture: null,
};

describe("workspace state helpers", () => {
  it("applies workspace summary to an existing workspace", () => {
    const result = applyWorkspaceSummaryList([baseWorkspace], {
      org_id: "org_001",
      member_count: 5,
      status: "syncing",
    });

    expect(result[0].member_count).toBe(5);
    expect(result[0].status).toBe("syncing");
  });

  it("merges a new workspace record into the list", () => {
    const result = mergeWorkspaceRecordList([
      { ...baseWorkspace, org_id: "org_002", name: "Team Beta" },
    ], baseWorkspace);

    expect(result).toHaveLength(2);
    expect(result.some((workspace) => workspace.org_id === "org_001")).toBe(true);
  });

  it("upserts invite records without duplicates", () => {
    const updatedInvite = { ...inviteA, status: "accepted" };
    const result = upsertInvite([inviteA, inviteB], updatedInvite);

    expect(result).toHaveLength(2);
    expect(result[0].status).toBe("accepted");
  });

  it("replaces a matching invite by id or email", () => {
    const updatedInvite = { ...inviteA, status: "resent" };
    const result = replaceInvite([inviteA, inviteB], "inv_a", updatedInvite);

    expect(result[0].status).toBe("resent");
  });

  it("removes invite and member items by id", () => {
    expect(removeInvite([inviteA, inviteB], "inv_a")).toEqual([inviteB]);
    expect(removeMember([memberA], 1)).toEqual([]);
  });
});
