function SummaryIcon({ path }: { path: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="stat-icon-svg" aria-hidden="true">
      <path d={path} />
    </svg>
  );
}

export function DashboardSummary(props: {
  totalTeams: number;
  totalMembers: number;
  availableSlots: number;
  pendingInvites: number;
}) {
  const items = [
    {
      icon: <SummaryIcon path="M4 7h16M7 4v6m10-6v6M5 11h14a1 1 0 0 1 1 1v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6a1 1 0 0 1 1-1Z" />,
      label: "Teams",
      value: props.totalTeams,
      meta: "Imported workspaces",
      tone: "accent",
    },
    {
      icon: <SummaryIcon path="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m16 0v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75M14 7a4 4 0 1 1-8 0a4 4 0 0 1 8 0Z" />,
      label: "Members",
      value: props.totalMembers,
      meta: "Active seats in use",
      tone: "success",
    },
    {
      icon: <SummaryIcon path="M3 11.5L12 4l9 7.5M5 10v8h14v-8M9 18v-4h6v4" />,
      label: "Available Slots",
      value: props.availableSlots,
      meta: "Empty seats remaining",
      tone: "accent",
    },
    {
      icon: <SummaryIcon path="M12 3l1.9 3.86L18 8.1l-3 2.93l.71 4.12L12 13.2l-3.71 1.95L9 11.03L6 8.1l4.1-.24L12 3Z" />,
      label: "Pending",
      value: props.pendingInvites,
      meta: "Invites awaiting reply",
      tone: "warning",
    },
  ];

  return (
    <section className="summary-strip" aria-label="Dashboard summary">
      <div className="summary-strip-kicker-wrap">
        <span className="summary-strip-kicker">Overview</span>
      </div>
      <div className="stats-grid">
        {items.map((item) => (
          <div key={item.label} className={`stat-card stat-${item.tone}`}>
            <div className="stat-topline">
              <span className="stat-icon" aria-hidden="true">{item.icon}</span>
              <div className="stat-copy">
                <span className="stat-label">{item.label}</span>
                <span className="stat-meta">{item.meta}</span>
              </div>
            </div>
            <div className="stat-value">{item.value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
