type WorkspaceCardProps = {
  title: string;
  members: number;
  memberLimit: number;
  status: "synced" | "warning" | "error";
  selected?: boolean;
};

export function WorkspaceCard({ title, members, memberLimit, status, selected }: WorkspaceCardProps) {
  const pct = memberLimit > 0 ? Math.round((members / memberLimit) * 100) : 0;
  const badgeClass = status === "synced" ? "badge-synced" : status === "warning" ? "badge-warning" : "badge-error";
  const statusLabel = status === "synced" ? "Active" : status === "warning" ? "Warning" : "Error";

  return (
    <div className={`workspace-card${selected ? " selected" : ""}`}>
      <div className="workspace-card-header">
        <div className="workspace-card-title">{title}</div>
        <span className={`workspace-badge ${badgeClass}`}>
          <span className="status-dot" /> {statusLabel}
        </span>
      </div>
      <div className="workspace-meta">
        <span>{members}/{memberLimit} members</span>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <span>{pct}%</span>
      </div>
    </div>
  );
}
