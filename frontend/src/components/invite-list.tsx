import type { Invite } from "@/types/api";

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "Just now";
  const d = new Date(dateStr);
  return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
}

export function InviteList({ invites }: { invites: Invite[] }) {
  if (invites.length === 0) return null;

  return (
    <div className="invite-list-shell">
      <div className="section-heading-row compact-heading-row">
        <div>
          <h3 className="section-heading">Pending invites</h3>
          <p className="section-description">Những lời mời đang chờ người nhận chấp nhận.</p>
        </div>
        <div className="section-count">{invites.length} pending</div>
      </div>

      <ul className="invite-list">
        {invites.map((invite) => (
          <li key={invite.id} className="invite-item">
            <div className="invite-item-main">
              <div className="invite-email">{invite.email}</div>
              <div className="invite-meta">Created {formatDate(invite.created_at)}</div>
            </div>
            <span className="role-pill role-pending">Pending</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
