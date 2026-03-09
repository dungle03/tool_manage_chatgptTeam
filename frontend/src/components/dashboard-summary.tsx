export function DashboardSummary(props: {
  totalTeams: number;
  totalMembers: number;
  pendingInvites: number;
  syncErrors: number;
}) {
  return (
    <section className="grid grid-cols-4 gap-3">
      <div>
        <span>Total teams</span>: {props.totalTeams}
      </div>
      <div>
        <span>Total members</span>: {props.totalMembers}
      </div>
      <div>
        <span>Pending invites</span>: {props.pendingInvites}
      </div>
      <div>
        <span>Sync errors</span>: {props.syncErrors}
      </div>
    </section>
  );
}
