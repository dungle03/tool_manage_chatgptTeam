"use client";

import { memo } from "react";

type CompactWorkspaceCardProps = {
  orgId: string;
  title: string;
  members: number;
  memberLimit: number;
  pendingInvites?: number;
  expiresAt?: string | null;
  accessTokenExpiresAt?: string | null;
  lastSync?: string | null;
  syncing?: boolean;
  status: "synced" | "warning" | "error";
  onRename?: () => void;
  onUpdateToken?: () => void;
  onSync?: () => void;
  onDelete?: () => void;
  onManage?: () => void;
};


type TokenStatusCopy = {
  label: string;
  value: string;
  tone: "success" | "neutral";
};

function MetaIcon({ type }: { type: "members" | "pending" }) {
  if (type === "members") {
    return (
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M13.5 16v-1a3.5 3.5 0 0 0-3.5-3.5H7A3.5 3.5 0 0 0 3.5 15v1" />
        <path d="M8.5 9a2.5 2.5 0 1 0 0-5a2.5 2.5 0 0 0 0 5Z" />
        <path d="M15.5 16v-1.1a3.13 3.13 0 0 0-2.2-3" />
        <path d="M13.1 4.2a2.4 2.4 0 0 1 0 4.6" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="10" cy="10" r="6.5" />
      <path d="M10 6.6v3.8l2.4 1.5" />
    </svg>
  );
}

function formatRelativeTime(timestamp?: string | null): string | null {
  if (!timestamp) return null;

  const target = new Date(timestamp).getTime();
  if (Number.isNaN(target)) return null;

  const diffSeconds = Math.max(Math.floor((Date.now() - target) / 1000), 0);

  if (diffSeconds < 60) return `${diffSeconds}s ago`;

  if (diffSeconds < 3600) {
    return `${Math.floor(diffSeconds / 60)}m ago`;
  }

  if (diffSeconds < 86400) {
    const hours = Math.floor(diffSeconds / 3600);
    const minutes = Math.floor((diffSeconds % 3600) / 60);
    return minutes > 0 ? `${hours}h ${minutes}m ago` : `${hours}h ago`;
  }

  const days = Math.floor(diffSeconds / 86400);
  const hours = Math.floor((diffSeconds % 86400) / 3600);
  return hours > 0 ? `${days}d ${hours}h ago` : `${days}d ago`;
}

function formatRemainingTime(timestamp?: string | null): string | null {
  if (!timestamp) return null;

  const target = new Date(timestamp).getTime();
  if (Number.isNaN(target)) return null;

  const diffSeconds = Math.max(Math.floor((target - Date.now()) / 1000), 0);
  const days = Math.floor(diffSeconds / 86400);
  const hours = Math.floor((diffSeconds % 86400) / 3600);
  const minutes = Math.floor((diffSeconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return "soon";
}

function formatDisplayDate(timestamp?: string | null): string | null {
  if (!timestamp) return null;

  const target = new Date(timestamp);
  if (Number.isNaN(target.getTime())) return null;

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(target);
}

function getTokenStatusCopy(
  accessTokenExpiresAt?: string | null,
  lastSync?: string | null,
): TokenStatusCopy {
  const tokenExpiryCopy = formatRemainingTime(accessTokenExpiresAt);
  if (tokenExpiryCopy) {
    return {
      label: "Access token expires in",
      value: tokenExpiryCopy,
      tone: "success",
    };
  }

  const lastSyncCopy = formatRelativeTime(lastSync);
  if (lastSyncCopy) {
    return {
      label: "Last sync",
      value: lastSyncCopy,
      tone: "neutral",
    };
  }

  return {
    label: "Token expiry",
    value: "unavailable",
    tone: "neutral",
  };
}

function CompactWorkspaceCardComponent({
  orgId,
  title,
  members,
  memberLimit,
  pendingInvites = 0,
  expiresAt,
  accessTokenExpiresAt,
  lastSync,
  syncing = false,
  status,
  onRename,
  onUpdateToken,
  onSync,
  onDelete,
  onManage,
}: CompactWorkspaceCardProps) {
  const seatLimit = memberLimit > 0 ? memberLimit : 7;
  const safeMembers = Math.min(members, seatLimit);
  const statusText = status === "synced" ? "LIVE" : "ISSUE";
  const tokenStatusCopy = getTokenStatusCopy(accessTokenExpiresAt, lastSync);
  const teamExpiryDate = formatDisplayDate(expiresAt);

  return (
    <article className={`compact-workspace-card compact-card-${status}`}>
      <div className="compact-card-toolbar">
        <button
          type="button"
          className={`compact-status compact-status-${status}`}
          id={`workspace-sync-compact-${orgId}`}
          onClick={onSync}
          disabled={syncing}
          aria-label={syncing ? `Workspace ${title} đang sync` : `Sync workspace ${title}`}
        >
          {syncing ? "SYNC" : statusText}
        </button>

        <div className="compact-toolbar-actions">
          <button
            type="button"
            className="compact-toolbar-icon"
            id={`workspace-rename-${orgId}`}
            onClick={onRename}
            aria-label={`Đổi tên workspace ${title}`}
          >
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M3 14.5V17h2.5L15 7.5 12.5 5 3 14.5Z" />
              <path d="M11.5 6 14 8.5" />
            </svg>
          </button>
          <button
            type="button"
            className="compact-toolbar-icon"
            id={`workspace-token-${orgId}`}
            onClick={onUpdateToken}
            aria-label={`Cập nhật token cho workspace ${title}`}
          >
            <svg
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              style={{ color: "#f5c451" }}
            >
              <circle cx="7.2" cy="10" r="2.7" />
              <path d="M9.9 10h6.35" />
              <path d="M13.2 10v2.2" />
              <path d="M15.55 10v1.55" />
            </svg>
          </button>
          <button
            type="button"
            className="compact-toolbar-icon"
            id={`workspace-refresh-${orgId}`}
            onClick={onSync}
            disabled={syncing}
            aria-label={`Đồng bộ workspace ${title}`}
          >
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M16.5 10a6.5 6.5 0 1 1-1.9-4.6" />
              <path d="M13.5 3.5h3v3" />
            </svg>
          </button>
          <button
            type="button"
            className="compact-toolbar-icon compact-toolbar-icon-danger"
            id={`workspace-delete-${orgId}`}
            onClick={onDelete}
            aria-label={`Xóa workspace ${title}`}
          >
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M4.5 6h11" />
              <path d="M8 3.5h4" />
              <path d="M6.5 6l.5 9a1 1 0 0 0 1 .94h3.98a1 1 0 0 0 1-.94l.52-9" />
              <path d="M8.5 9.5v3.5" />
              <path d="M11.5 9.5v3.5" />
            </svg>
          </button>
        </div>
      </div>

      <div className="compact-title-stack">
        <h3 className="compact-workspace-title">{title}</h3>
        <span className="compact-team-badge">team</span>
      </div>

      <div className="compact-info-list">
        <div className="compact-info-row">
          <span className="compact-info-label">
            <span className="compact-info-symbol"><MetaIcon type="members" /></span>
            <span>Members</span>
          </span>
          <strong>{safeMembers} / {seatLimit}</strong>
        </div>
        <div className="compact-info-row">
          <span className="compact-info-label">
            <span className="compact-info-symbol"><MetaIcon type="pending" /></span>
            <span>Pending</span>
          </span>
          <strong>{pendingInvites}</strong>
        </div>
      </div>

      <div className="compact-card-divider" />

      <div className={`compact-token-row compact-token-row-${tokenStatusCopy.tone}`}>
        <span className="compact-token-icon" aria-hidden="true">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M7.5 10a2.5 2.5 0 1 1 4.3 1.77l-4.08 4.08a2.5 2.5 0 1 1-3.54-3.54l1.6-1.6" />
            <path d="M12.5 10a2.5 2.5 0 1 1-4.3-1.77l4.08-4.08a2.5 2.5 0 1 1 3.54 3.54l-1.6 1.6" />
          </svg>
        </span>
        <span className="compact-token-copy">{tokenStatusCopy.label}</span>
        <strong>{tokenStatusCopy.value}</strong>
      </div>

      {teamExpiryDate ? (
        <div className="compact-token-row compact-token-row-neutral">
          <span className="compact-token-icon" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3.5" y="4.5" width="13" height="12" rx="2.5" />
              <path d="M6.5 3.5v3" />
              <path d="M13.5 3.5v3" />
              <path d="M3.5 8.5h13" />
            </svg>
          </span>
          <span className="compact-token-copy">Team expires on</span>
          <strong>{teamExpiryDate}</strong>
        </div>
      ) : null}

      <div className="compact-card-actions">
        <button
          type="button"
          className="btn compact-manage-btn"
          onClick={onManage}
          id={`workspace-manage-${orgId}`}
        >
          <span>Manage Team</span>
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M7 5l5 5-5 5" />
          </svg>
        </button>
      </div>

      <span className="compact-card-org-id">{orgId}</span>
    </article>
  );
}

export const CompactWorkspaceCard = memo(CompactWorkspaceCardComponent);
