import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildWorkspaceEventsUrl,
  getWorkspaces,
  invalidateApiCache,
  parseWorkspaceEvent,
} from "@/lib/api";

describe("workspace realtime helpers", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "http://localhost:3000/");
  });

  it("builds workspace events url", () => {
    expect(buildWorkspaceEventsUrl()).toBe("http://localhost:3000/api/events/workspaces");
  });

  it("parses workspace events payload", () => {
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

  it("invalidates GET cache when requested", async () => {
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
