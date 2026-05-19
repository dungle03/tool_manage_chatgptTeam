import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  checkPersonalAccount,
  completePersonalAccountOAuthWithCallbackUrl,
  deletePersonalAccount,
  getPersonalAccounts,
  getWorkspaces,
  invalidateApiCache,
  refreshPersonalAccount,
  resolvePersonalAccountDuplicate,
  startPersonalAccountOAuth,
  startPersonalAccountReconnect,
} from "@/lib/api";

describe("api client", () => {
  beforeEach(() => {
    invalidateApiCache();
    vi.unstubAllGlobals();
  });

  it("calls GET /api/workspaces", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal("fetch", mockFetch as any);

    await getWorkspaces();
    expect(mockFetch).toHaveBeenCalledWith("/api/workspaces", expect.any(Object));
  });

  it("bypasses cached GET results when forceFresh is enabled", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [{ org_id: "cached" }] })
      .mockResolvedValueOnce({ ok: true, json: async () => [{ org_id: "fresh" }] });

    vi.stubGlobal("fetch", mockFetch as any);

    const cached = await getWorkspaces();
    const fresh = await getWorkspaces({ forceFresh: true });

    expect(cached).toEqual([{ org_id: "cached" }]);
    expect(fresh).toEqual([{ org_id: "fresh" }]);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("wires Personal Accounts endpoints", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", mockFetch as any);

    await getPersonalAccounts({ forceFresh: true });
    await startPersonalAccountOAuth();
    await completePersonalAccountOAuthWithCallbackUrl("http://localhost:8484/callback?code=abc&state=state-1");
    await resolvePersonalAccountDuplicate("dupe-token", "overwrite_existing");
    await refreshPersonalAccount(11);
    await checkPersonalAccount(11);
    await startPersonalAccountReconnect(11);
    await deletePersonalAccount(11);

    expect(mockFetch).toHaveBeenNthCalledWith(1, "/api/personal-accounts", expect.objectContaining({ method: "GET" }));
    expect(mockFetch).toHaveBeenNthCalledWith(2, "/api/personal-accounts/oauth/start", expect.objectContaining({ method: "POST" }));
    expect(mockFetch).toHaveBeenNthCalledWith(
      3,
      "/api/personal-accounts/oauth/callback-url",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ callback_url: "http://localhost:8484/callback?code=abc&state=state-1" }),
      }),
    );
    expect(mockFetch).toHaveBeenNthCalledWith(
      4,
      "/api/personal-accounts/oauth/resolve-duplicate",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ duplicate_token: "dupe-token", decision: "overwrite_existing" }),
      }),
    );
    expect(mockFetch).toHaveBeenNthCalledWith(5, "/api/personal-accounts/11/refresh", expect.objectContaining({ method: "POST" }));
    expect(mockFetch).toHaveBeenNthCalledWith(6, "/api/personal-accounts/11/check", expect.objectContaining({ method: "POST" }));
    expect(mockFetch).toHaveBeenNthCalledWith(7, "/api/personal-accounts/11/reconnect/start", expect.objectContaining({ method: "POST" }));
    expect(mockFetch).toHaveBeenNthCalledWith(8, "/api/personal-accounts/11", expect.objectContaining({ method: "DELETE" }));
  });
});

