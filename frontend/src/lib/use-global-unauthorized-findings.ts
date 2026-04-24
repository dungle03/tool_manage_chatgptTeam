"use client";

import { useCallback, useState } from "react";
import { listAllUnauthorizedFindings } from "@/lib/api";
import type { GlobalUnauthorizedFinding } from "@/lib/api";

function isActiveUnauthorizedFinding(finding: GlobalUnauthorizedFinding): boolean {
  return finding.status === "detected" || finding.status === "kick_failed";
}

export function useGlobalUnauthorizedFindings() {
  const [findings, setFindings] = useState<GlobalUnauthorizedFinding[]>([]);
  const [dismissed, setDismissed] = useState(false);

  const refreshFindings = useCallback(async () => {
    try {
      const nextFindings = await listAllUnauthorizedFindings({ forceFresh: true });
      setFindings(nextFindings.filter(isActiveUnauthorizedFinding));
      setDismissed(false);
    } catch {
      // Banner is optional; keep dashboard usable if this request fails.
    }
  }, []);

  const dismissFindings = useCallback(() => {
    setDismissed(true);
  }, []);

  return {
    findings,
    dismissed,
    refreshFindings,
    dismissFindings,
  };
}
