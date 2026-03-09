import { describe, it, expect, vi } from "vitest";
import { getWorkspaces } from "@/lib/api";

describe("api client", () => {
  it("calls GET /api/workspaces", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal("fetch", mockFetch as any);

    await getWorkspaces();
    expect(mockFetch).toHaveBeenCalledWith("/api/workspaces", expect.any(Object));
  });
});
