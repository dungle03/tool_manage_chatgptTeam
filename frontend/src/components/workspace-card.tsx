"use client";

import { useState, ReactNode } from "react";

type WorkspaceCardProps = {
  title: string;
  members: number;
  memberLimit: number;
  status: "synced" | "warning" | "error";
  selected?: boolean;
  lastSync?: string | null;
  syncing?: boolean;
  expandedContent?: ReactNode;
  onSync?: () => void;
  onInvite?: () => void;
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

export function WorkspaceCard({
  title,
  members,
  memberLimit,
  status,
  selected,
  lastSync,
  syncing = false,
  expandedContent,
  onSync,
  onInvite,
  onDelete,
  onExpandedChange,
}: WorkspaceCardProps) {
  const [expanded, setExpanded] = useState(selected ?? false);
  const seatLimit = 5;
  const pct = seatLimit > 0 ? Math.min(100, Math.round((members / seatLimit) * 100)) : 0;
  const statusLabel = status === "synced" ? "Live" : status === "warning" ? "Needs sync" : "Issue";
  const badgeClass =
    status === "synced" ? "badge-synced" : status === "warning" ? "badge-warning" : "badge-error";

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
          id={`workspace-toggle-${title.replace(/\s+/g, "-").toLowerCase()}`}
        >
          <div className="workspace-card-heading">
            <span className="workspace-chevron" aria-hidden="true">{expanded ? "⌄" : "›"}</span>
            <div className="workspace-title-stack">
              <div className="workspace-title-row">
                <span className="workspace-card-title">{title}</span>
                <span className={`workspace-badge ${badgeClass}`}>{statusLabel}</span>
              </div>
              <div className="workspace-meta-row">
                <span>{members} members</span>
                <span className="meta-dot">•</span>
                <span>Last sync {formatSyncTime(lastSync)}</span>
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
              onInvite?.();
            }}
            className="btn btn-secondary btn-compact"
            id={`workspace-invite-${title.replace(/\s+/g, "-").toLowerCase()}`}
          >
            Invite
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSync?.();
            }}
            disabled={syncing}
            className="btn btn-secondary btn-compact"
            id={`workspace-sync-${title.replace(/\s+/g, "-").toLowerCase()}`}
          >
            <span style={{ display: "inline-block", animation: syncing ? "spin 1s linear infinite" : "none" }}>
              ↺
            </span>
            {syncing ? "Syncing" : "Sync"}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete?.();
            }}
            className="btn btn-danger btn-compact"
            id={`workspace-delete-${title.replace(/\s+/g, "-").toLowerCase()}`}
          >
            Delete
          </button>
        </div>
      </div>

      {expanded && expandedContent && <div className="workspace-accordion-content">{expandedContent}</div>}
    </section>
  );
}
