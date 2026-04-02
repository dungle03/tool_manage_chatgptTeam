import { beforeEach, describe, expect, it, vi } from "vitest";
import { getWorkspaces, invalidateApiCache } from "@/lib/api";

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
});
