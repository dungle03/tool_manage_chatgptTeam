import { inviteMember, kickMember, listInvites, resendInvite, cancelInvite, syncWorkspace } from "@/lib/api";
import { describe, it, expect, vi } from "vitest";

describe("endpoint wiring", () => {
  it("hits required backend API paths", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", mockFetch as any);

    await inviteMember({ org_id: "org_001", email: "a@x.com" });
    await kickMember({ org_id: "org_001", member_id: 1 });
    await listInvites("org_001");
    await resendInvite({ org_id: "org_001", invite_id: "inv_1" });
    await cancelInvite({ org_id: "org_001", invite_id: "inv_1" });
    await syncWorkspace("org_001");

    const calledUrls = mockFetch.mock.calls.map((x: any[]) => x[0]);
    expect(calledUrls).toContain("/api/invite");
    expect(calledUrls).toContain("/api/member");
    expect(calledUrls).toContain("/api/invites?org_id=org_001");
    expect(calledUrls).toContain("/api/resend-invite");
    expect(calledUrls).toContain("/api/cancel-invite");
    expect(calledUrls).toContain("/api/workspaces/org_001/sync");

    const syncCall = mockFetch.mock.calls.find((x: any[]) => x[0] === "/api/workspaces/org_001/sync");
    expect(syncCall?.[1]?.method).toBe("POST");
  });
});
