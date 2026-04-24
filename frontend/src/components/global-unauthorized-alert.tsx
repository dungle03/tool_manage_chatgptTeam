"use client";

import type { GlobalUnauthorizedFinding } from "@/lib/api";

const findingStatusTone: Record<GlobalUnauthorizedFinding["status"], "synced" | "error" | "warning"> = {
  kicked: "synced",
  kick_failed: "error",
  trusted: "warning",
  detected: "warning",
};

const findingStatusLabel: Record<GlobalUnauthorizedFinding["status"], string> = {
  kicked: "Kicked",
  kick_failed: "Kick failed",
  trusted: "Trusted",
  detected: "Detected",
};

const findingDotClass: Record<GlobalUnauthorizedFinding["status"], string> = {
  kicked: "unauthorized-alert-dot-synced",
  kick_failed: "unauthorized-alert-dot-error",
  trusted: "unauthorized-alert-dot-warning",
  detected: "unauthorized-alert-dot-warning",
};

type GlobalUnauthorizedAlertProps = {
  findings: GlobalUnauthorizedFinding[];
  onDismiss: () => void;
};

function formatFindingDate(timestamp: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

export function GlobalUnauthorizedAlert({
  findings,
  onDismiss,
}: GlobalUnauthorizedAlertProps) {
  if (findings.length === 0) {
    return null;
  }

  return (
    <div className="section-panel unauthorized-alert-panel">
      <div className="unauthorized-alert-header">
        <div>
          <h3 className="section-heading unauthorized-alert-title">
            ⚠️ Unauthorized Member Alert — {findings.length} active case{findings.length > 1 ? "s" : ""}
          </h3>
          <p className="section-description unauthorized-alert-description">
            Các thành viên dưới đây đang là case chưa xử lý dứt điểm trong local whitelist. Nếu auto-kick thành công thì case sẽ tự biến mất khỏi banner này.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-compact unauthorized-alert-dismiss"
          onClick={onDismiss}
        >
          Dismiss
        </button>
      </div>

      <div className="unauthorized-alert-list">
        {findings.map((finding) => (
          <div key={finding.id} className="unauthorized-alert-item">
            <span className={`unauthorized-alert-dot ${findingDotClass[finding.status]}`} />
            <strong className="unauthorized-alert-email">{finding.email}</strong>
            <span className="workspace-helper-copy">
              → team <strong>{finding.workspace_name}</strong>
            </span>
            <span className="workspace-helper-copy">
              Detected: {formatFindingDate(finding.first_seen_at)}
            </span>
            {finding.resolved_at && (
              <span className="workspace-helper-copy">
                Kicked: {formatFindingDate(finding.resolved_at)}
              </span>
            )}
            <span className={`workspace-badge badge-${findingStatusTone[finding.status]} unauthorized-alert-status`}>
              {findingStatusLabel[finding.status]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
