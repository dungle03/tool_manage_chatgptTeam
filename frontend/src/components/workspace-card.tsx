"use client";

import { memo, useEffect, useState, ReactNode } from "react";

type WorkspaceCardProps = {
  orgId: string;
  title: string;
  members: number;
  memberLimit: number;
  status: "synced" | "warning" | "error";
  selected?: boolean;
  lastSync?: string | null;
  expiresAt?: string | null;
  accessTokenExpiresAt?: string | null;
  syncing?: boolean;
  isHot?: boolean;
  syncReason?: string | null;
  expandedContent?: ReactNode;
  onRename?: () => void;
  onUpdateToken?: () => void;
  onSync?: () => void;
  onDelete?: () => void;
  onExpandedChange?: (expanded: boolean) => void;
};


function formatSyncTime(lastSync?: string | null): string {
  if (!lastSync) return "Chưa sync";
  const diff = Math.floor((Date.now() - new Date(lastSync).getTime()) / 1000);
  if (diff < 60) return `${diff}s trước`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m trước`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h trước`;
  return `${Math.floor(diff / 86400)}d trước`;
}

function formatReason(reason?: string | null): string | null {
  if (!reason) return null;
  if (reason === "pending_invite_watch") return "Watching invites";
  if (reason === "invite_created") return "Invite follow-up";
  if (reason === "invite_resend") return "Resend follow-up";
  if (reason === "invite_cancelled") return "Cancel follow-up";
  if (reason === "member_kicked") return "Member update watch";
  if (reason === "manual_sync") return "Manual sync watch";
  if (reason === "workspace_imported") return "Import warm-up";
  if (reason === "retry_after_error") return "Retry scheduled";
  if (reason.startsWith("followup:")) return "Hot follow-up";
  if (reason === "baseline_refresh") return "Baseline refresh";
  return reason;
}

function formatDateLabel(prefix: string, timestamp?: string | null): string {
  if (!timestamp) return `${prefix}: Chưa rõ`;

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return `${prefix}: Chưa rõ`;
  }

  const day = String(date.getUTCDate()).padStart(2, "0");
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const year = date.getUTCFullYear();
  return `${prefix}: ${day}/${month}/${year}`;
}

function formatTokenTimeRemaining(accessTokenExpiresAt?: string | null): string {
  if (!accessTokenExpiresAt) return "Token hết hạn: Chưa rõ";

  const target = new Date(accessTokenExpiresAt).getTime();
  if (Number.isNaN(target)) {
    return "Token hết hạn: Chưa rõ";
  }

  const diffSeconds = Math.max(Math.floor((target - Date.now()) / 1000), 0);
  const days = Math.floor(diffSeconds / 86400);
  const hours = Math.floor((diffSeconds % 86400) / 3600);
  const minutes = Math.floor((diffSeconds % 3600) / 60);

  if (days > 0) return `Token hết hạn sau ${days}d ${hours}h`;
  if (hours > 0) return `Token hết hạn sau ${hours}h ${minutes}m`;
  if (minutes > 0) return `Token hết hạn sau ${minutes}m`;
  return "Token hết hạn: sắp tới";
}

function WorkspaceCardComponent({
  orgId,
  title,
  members,
  memberLimit,
  status,
  selected,
  lastSync,
  expiresAt,
  accessTokenExpiresAt,
  syncing = false,
  isHot = false,
  syncReason,
  expandedContent,
  onRename,
  onUpdateToken,
  onSync,
  onDelete,
  onExpandedChange,
}: WorkspaceCardProps) {
  const [expanded, setExpanded] = useState(selected ?? false);
  const seatLimit = memberLimit > 0 ? memberLimit : 7;
  const pct = seatLimit > 0 ? Math.min(100, Math.round((members / seatLimit) * 100)) : 0;
  const statusLabel = status === "synced" ? "Live" : status === "warning" ? "Needs sync" : "Issue";
  const badgeClass =
    status === "synced" ? "badge-synced" : status === "warning" ? "badge-warning" : "badge-error";
  const reasonLabel = formatReason(syncReason);

  useEffect(() => {
    if (selected === undefined) {
      return;
    }
    setExpanded(selected);
  }, [selected]);

  return (
    <section className={`workspace-card${expanded ? " selected" : ""}`}>
      <div className="workspace-card-header">
        <button
          aria-label={expanded ? `Thu gọn ${title}` : `Mở ${title}`}
          className="workspace-card-main"
          onClick={() => {
            setExpanded((prev) => {
              const next = !prev;
              onExpandedChange?.(next);
              return next;
            });
          }}
          id={`workspace-toggle-${orgId}`}
        >
          <div className="workspace-card-heading">
            <span
              className={`workspace-chevron${expanded ? " is-expanded" : ""}`}
              aria-hidden="true"
            >
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 4.75 12.5 10 7 15.25" />
              </svg>
            </span>
            <div className="workspace-title-stack">
              <div className="workspace-title-row">
                <span className="workspace-card-title">{title}</span>
                <button
                  type="button"
                  className="workspace-rename-trigger"
                  id={`workspace-rename-default-${orgId}`}
                  aria-label={`Đổi tên workspace ${title}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    onRename?.();
                  }}
                >
                  ✎
                </button>
                <span className={`workspace-badge ${badgeClass}`}>{statusLabel}</span>
                {isHot && <span className="workspace-badge badge-warning">Hot</span>}
              </div>
              <div className="workspace-meta-subline">{formatTokenTimeRemaining(accessTokenExpiresAt)}</div>
              <div className="workspace-meta-row">
                <span>{members} members</span>
                <span className="meta-dot">•</span>
                <span>{formatDateLabel("Plan", expiresAt)}</span>
                <span className="meta-dot">•</span>
                <span>Last sync {formatSyncTime(lastSync)}</span>
                {reasonLabel && (
                  <>
                    <span className="meta-dot">•</span>
                    <span>{reasonLabel}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="workspace-capacity">
            <div className="workspace-capacity-label">
              <span>Seat usage</span>
              <strong>
                {members}/{seatLimit}
              </strong>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
        </button>

        <div className="workspace-actions">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onUpdateToken?.();
            }}
            className="btn btn-secondary btn-compact workspace-sync-btn"
            id={`workspace-token-${orgId}`}
            aria-label={`Cập nhật token cho workspace ${title}`}
            title="Cập nhật token"
          >
            <span className="sync-icon" aria-hidden="true">
              <svg
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ color: "#f5c451" }}
              >
                <circle cx="7.2" cy="10" r="2.7" />
                <path d="M9.9 10h6.35" />
                <path d="M13.2 10v2.2" />
                <path d="M15.55 10v1.55" />
              </svg>
            </span>
            <span className="workspace-sync-label">Token</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSync?.();
            }}
            disabled={syncing}
            className="btn btn-secondary btn-compact workspace-sync-btn"
            id={`workspace-sync-${orgId}`}
          >
            <span className={`sync-icon${syncing ? " is-spinning" : ""}`} aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16.2 10a6.2 6.2 0 0 1-10.58 4.38" />
                <path d="M3.8 10a6.2 6.2 0 0 1 10.58-4.38" />
                <path d="M4.45 13.9H5.8v-1.36" />
                <path d="M14.2 6.1h1.35V7.46" />
              </svg>
            </span>
            <span className="workspace-sync-label">{syncing ? "Syncing" : "Sync"}</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete?.();
            }}
            className="btn btn-danger btn-compact"
            id={`workspace-delete-${orgId}`}
          >
            Delete
          </button>
        </div>
      </div>

      {expanded && expandedContent && <div className="workspace-accordion-content">{expandedContent}</div>}
    </section>
  );
}

export const WorkspaceCard = memo(WorkspaceCardComponent);
