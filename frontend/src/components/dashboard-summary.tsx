export function DashboardSummary(props: {
  totalTeams: number;
  totalMembers: number;
  pendingInvites: number;
  syncErrors: number;
}) {
  return (
    <div className="stats-grid">
      <div className="stat-card accent">
        <div className="stat-icon">🏢</div>
        <div className="stat-label">Total teams</div>
        <div className="stat-value">{props.totalTeams}</div>
      </div>
      <div className="stat-card success">
        <div className="stat-icon">👥</div>
        <div className="stat-label">Total members</div>
        <div className="stat-value">{props.totalMembers}</div>
      </div>
      <div className="stat-card warning">
        <div className="stat-icon">📩</div>
        <div className="stat-label">Pending invites</div>
        <div className="stat-value">{props.pendingInvites}</div>
      </div>
      <div className="stat-card danger">
        <div className="stat-icon">⚠️</div>
        <div className="stat-label">Sync errors</div>
        <div className="stat-value">{props.syncErrors}</div>
      </div>
    </div>
  );
}
