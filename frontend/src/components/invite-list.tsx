import type { Invite } from "@/types/api";

export function InviteList({ invites }: { invites: Invite[] }) {
  if (invites.length === 0) return null;

  const statusClass = (s: string) =>
    s === "pending" ? "status-pending" : s === "cancelled" ? "status-removed" : "status-active";

  return (
    <ul className="invite-list">
      {invites.map((invite) => (
        <li key={invite.id} className="invite-item">
          <span className="invite-email">{invite.email}</span>
          <span className={`status-badge ${statusClass(invite.status)}`}>
            <span className="status-dot" />
            {invite.status}
          </span>
        </li>
      ))}
    </ul>
  );
}
