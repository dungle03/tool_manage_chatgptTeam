import { beforeEach, describe, expect, it, vi } from "vitest";

describe("workspace realtime helpers", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "http://localhost:3000/");
  });

  it("builds workspace events url without token by default", async () => {
    vi.stubEnv("NEXT_PUBLIC_ADMIN_TOKEN", "");
    const { buildWorkspaceEventsUrl } = await import("@/lib/api");

    expect(buildWorkspaceEventsUrl()).toBe("http://localhost:3000/api/events/workspaces");
  });

  it("appends admin token to workspace events url when configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_ADMIN_TOKEN", "secret-token");
    const { buildWorkspaceEventsUrl } = await import("@/lib/api");

    expect(buildWorkspaceEventsUrl()).toBe(
      "http://localhost:3000/api/events/workspaces?admin_token=secret-token",
    );
  });

  it("parses workspace events payload", async () => {
    const { parseWorkspaceEvent } = await import("@/lib/api");

    const event = parseWorkspaceEvent(
      JSON.stringify({
        type: "workspace_updated",
        org_id: "org_001",
        timestamp: "2026-03-11T14:00:00Z",
        sequence: 1,
      }),
    );

    expect(event.type).toBe("workspace_updated");
    expect(event.org_id).toBe("org_001");
  });

  it("throws on malformed workspace event payload", async () => {
    const { parseWorkspaceEvent } = await import("@/lib/api");

    expect(() => parseWorkspaceEvent("not-json")).toThrow();
  });

  it("invalidates GET cache when requested", async () => {
    vi.stubEnv("NEXT_PUBLIC_ADMIN_TOKEN", "");
    const { getWorkspaces, invalidateApiCache } = await import("@/lib/api");
    const mockFetch = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => [] })
      .mockResolvedValueOnce({ ok: true, json: async () => [{ org_id: "org_001" }] });

    vi.stubGlobal("fetch", mockFetch as never);

    await getWorkspaces();
    await getWorkspaces();
    expect(mockFetch).toHaveBeenCalledTimes(1);

    invalidateApiCache();
    await getWorkspaces();
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});
