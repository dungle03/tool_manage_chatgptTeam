"use client";

import type {
  UnauthorizedFinding,
  UnauthorizedFindingStatus,
  UnauthorizedMemberMode,
} from "@/types/api";

type UnauthorizedMembersPanelProps = {
  orgId: string;
  mode: UnauthorizedMemberMode;
  findings: UnauthorizedFinding[];
  canManage: boolean;
  submittingMode: boolean;
  busyFindingActions: Record<number, "trust" | "kick">;
  onModeChange?: (mode: UnauthorizedMemberMode) => void;
  onTrust?: (findingId: number) => void;
  onKick?: (findingId: number) => void;
};

const MODE_OPTIONS: Array<{ value: UnauthorizedMemberMode; label: string; help: string }> = [
  {
    value: "off",
    label: "Off",
    help: "Chỉ sync dữ liệu, không đánh dấu unauthorized member.",
  },
  {
    value: "warn_only",
    label: "Warn only",
    help: "Phát hiện member lạ và hiển thị trong dashboard để bạn xử lý tay.",
  },
  {
    value: "auto_kick",
    label: "Auto kick",
    help: "Phát hiện member lạ trong lúc sync và tự động kick nếu upstream cho phép.",
  },
];

function formatTimestamp(value?: string | null): string {
  if (!value) return "Chưa có";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Chưa có";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function statusCopy(status: UnauthorizedFindingStatus): { label: string; tone: string } {
  switch (status) {
    case "detected":
      return { label: "Detected", tone: "warning" };
    case "kick_failed":
      return { label: "Kick failed", tone: "error" };
    case "kicked":
      return { label: "Kicked", tone: "success" };
    case "trusted":
      return { label: "Trusted", tone: "neutral" };
    default:
      return { label: status, tone: "neutral" };
  }
}

export function UnauthorizedMembersPanel({
  orgId,
  mode,
  findings,
  canManage,
  submittingMode,
  busyFindingActions,
  onModeChange,
  onTrust,
  onKick,
}: UnauthorizedMembersPanelProps) {
  const activeFindings = findings.filter(
    (finding) => finding.status === "detected" || finding.status === "kick_failed"
  );

  return (
    <section className="section-panel invite-section-panel">
      <div className="section-heading-row compact-heading-row">
        <div>
          <h3 className="section-heading">Unauthorized members</h3>
          <p className="section-description">
            Local database là whitelist. Member nào có trên ChatGPT nhưng không có trong local DB sẽ xuất hiện ở đây.
          </p>
        </div>
        <span className="workspace-badge badge-warning">{activeFindings.length} active</span>
      </div>

      <div
        style={{
          display: "grid",
          gap: 10,
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          marginBottom: 16,
        }}
      >
        {MODE_OPTIONS.map((option) => {
          const selected = option.value === mode;
          return (
            <button
              key={option.value}
              type="button"
              id={`unauthorized-mode-${orgId}-${option.value}`}
              className={`btn ${selected ? "btn-primary" : "btn-secondary"}`}
              onClick={() => onModeChange?.(option.value)}
              disabled={!canManage || submittingMode}
              style={{
                justifyContent: "flex-start",
                textAlign: "left",
                minHeight: 84,
                opacity: !canManage && !selected ? 0.75 : 1,
              }}
            >
              <span>
                <strong style={{ display: "block", marginBottom: 4 }}>{option.label}</strong>
                <span style={{ fontSize: 12, opacity: 0.82 }}>{option.help}</span>
              </span>
            </button>
          );
        })}
      </div>

      {findings.length === 0 ? (
        <div className="workspace-helper-copy">
          Chưa có unauthorized member nào được phát hiện cho workspace này.
        </div>
      ) : (
        <div style={{ display: "grid", gap: 12 }}>
          {findings.map((finding) => {
            const status = statusCopy(finding.status);
            const busyAction = busyFindingActions[finding.id];
            const actionable = finding.status === "detected" || finding.status === "kick_failed";

            return (
              <article
                key={finding.id}
                style={{
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 16,
                  padding: 14,
                  background: "rgba(255,255,255,0.03)",
                  display: "grid",
                  gap: 10,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <div>
                    <strong style={{ display: "block" }}>{finding.name || finding.email}</strong>
                    <span className="workspace-helper-copy">{finding.email}</span>
                  </div>
                  <span className={`workspace-badge badge-${status.tone}`}>{status.label}</span>
                </div>

                <div className="workspace-helper-copy" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <span>Role: {finding.role}</span>
                  <span className="meta-dot">•</span>
                  <span>First seen: {formatTimestamp(finding.first_seen_at)}</span>
                  <span className="meta-dot">•</span>
                  <span>Last seen: {formatTimestamp(finding.last_seen_at)}</span>
                </div>

                {finding.action_reason && (
                  <div className="workspace-helper-copy">Reason: {finding.action_reason}</div>
                )}

                {actionable && canManage ? (
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      id={`unauthorized-trust-${orgId}-${finding.id}`}
                      onClick={() => onTrust?.(finding.id)}
                      disabled={Boolean(busyAction)}
                    >
                      {busyAction === "trust" ? "Đang trust..." : "Trust local whitelist"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger"
                      id={`unauthorized-kick-${orgId}-${finding.id}`}
                      onClick={() => onKick?.(finding.id)}
                      disabled={Boolean(busyAction)}
                    >
                      {busyAction === "kick" ? "Đang kick..." : "Kick upstream"}
                    </button>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
