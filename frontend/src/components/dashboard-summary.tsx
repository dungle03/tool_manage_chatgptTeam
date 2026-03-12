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
  // Health is temporarily hidden to keep the summary grid balanced.
  // If we want to show it again later, restore both:
  // 1) the syncErrors prop passed from page.tsx
  // 2) the Health item inside the items array below
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
      meta: "Invites waiting response",
      tone: "warning",
    },
  ];

  return (
    <div className="stats-grid">
      {items.map((item) => (
        <div key={item.label} className={`stat-card stat-${item.tone}`}>
          <div className="stat-topline">
            <span className="stat-icon" aria-hidden="true">{item.icon}</span>
            <span className="stat-label">{item.label}</span>
          </div>
          <div className="stat-value">{item.value}</div>
          <div className="stat-meta">{item.meta}</div>
        </div>
      ))}
    </div>
  );
}
