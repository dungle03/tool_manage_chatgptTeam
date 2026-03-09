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
  onEdit?: () => void;
  onDelete?: () => void;
};

function formatSyncTime(lastSync?: string | null): string {
  if (!lastSync) return "Chưa sync";
  const diff = Math.floor((Date.now() - new Date(lastSync).getTime()) / 1000);
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  return `${Math.floor(diff / 3600)}h`;
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
  onEdit,
  onDelete,
}: WorkspaceCardProps) {
  const [expanded, setExpanded] = useState(selected ?? false);
  const pct = memberLimit > 0 ? Math.round((members / memberLimit) * 100) : 0;
  const statusLabel = status === "synced" ? "SỐNG" : status === "warning" ? "CẢNH BÁO" : "LỖI";
  const badgeClass =
    status === "synced" ? "badge-synced" : status === "warning" ? "badge-warning" : "badge-error";

  return (
    <div className={`workspace-card${expanded ? " selected" : ""}`}>
      {/* Accordion Header */}
      <div className="workspace-card-header" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        {/* Toggle Button */}
        <button
          aria-label={title}
          onClick={() => setExpanded((v) => !v)}
          style={{
            background: "none",
            border: "none",
            color: "var(--text-primary)",
            cursor: "pointer",
            fontSize: "16px",
            padding: "0 4px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            flex: 1,
            minWidth: 0,
          }}
        >
          <span style={{ fontSize: "12px", opacity: 0.6 }}>{expanded ? "▼" : "▶"}</span>
          <span className="workspace-card-title" style={{ fontWeight: 600, fontSize: "15px" }}>
            {title}
          </span>
        </button>

        {/* Status Badge */}
        <span className={`workspace-badge ${badgeClass}`} style={{ flexShrink: 0 }}>
          <span className="status-dot" /> {statusLabel}
        </span>

        {/* Sync time */}
        <span style={{ fontSize: "12px", opacity: 0.5, flexShrink: 0 }}>{formatSyncTime(lastSync)}</span>

        {/* Progress bar */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0, minWidth: "120px" }}>
          <div className="progress-bar" style={{ flex: 1 }}>
            <div className="progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <span style={{ fontSize: "12px", opacity: 0.65, whiteSpace: "nowrap" }}>
            {members}/{memberLimit}
          </span>
        </div>

        {/* Toolbar */}
        <div style={{ display: "flex", gap: "4px", flexShrink: 0 }}>
          <button
            onClick={onInvite}
            title="Mời thành viên"
            style={toolbarBtnStyle}
          >
            +
          </button>
          <button
            onClick={onSync}
            title="Sync"
            disabled={syncing}
            style={{ ...toolbarBtnStyle, opacity: syncing ? 0.5 : 1 }}
          >
            <span style={{ display: "inline-block", animation: syncing ? "spin 1s linear infinite" : "none" }}>↺</span>
          </button>
          <button
            onClick={onEdit}
            title="Chỉnh sửa"
            style={toolbarBtnStyle}
          >
            ✏️
          </button>
          <button
            onClick={onDelete}
            title="Xóa workspace"
            style={{ ...toolbarBtnStyle, color: "var(--danger)" }}
          >
            🗑️
          </button>
        </div>
      </div>

      {/* Accordion Content */}
      {expanded && expandedContent && (
        <div className="workspace-accordion-content" data-testid="accordion-content">
          {expandedContent}
        </div>
      )}
    </div>
  );
}

const toolbarBtnStyle: React.CSSProperties = {
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "5px",
  color: "var(--text-secondary)",
  cursor: "pointer",
  fontSize: "13px",
  padding: "3px 8px",
  lineHeight: 1,
};
