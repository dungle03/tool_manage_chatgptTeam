import type { Invite } from "@/types/api";

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "Just now";
  const d = new Date(dateStr);
  return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
}

type InviteListProps = {
  invites: Invite[];
  busyInviteActions?: Record<string, "resend" | "revoke">;
  onResend?: (inviteId: string) => Promise<void>;
  onRevoke?: (inviteId: string) => Promise<void>;
};

export function InviteList({ invites, busyInviteActions = {}, onResend, onRevoke }: InviteListProps) {
  if (invites.length === 0) return null;

  const canManageInvites = Boolean(onResend || onRevoke);

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
        {invites.map((invite) => {
          const busyAction = busyInviteActions[invite.invite_id];
          const isBusy = Boolean(busyAction);

          return (
            <li key={invite.id} className={`invite-item${isBusy ? " invite-item-busy" : ""}`}>
              <div className="invite-item-main">
                <div className="invite-email" title={invite.email}>{invite.email}</div>
                <div className="invite-meta">Created {formatDate(invite.created_at)}</div>
              </div>

              <div className="invite-item-footer">
                <span className="role-pill role-pending">Pending</span>
                {canManageInvites && (
                  <div className="invite-item-actions">
                    {onResend && (
                      <button
                        className="btn btn-secondary btn-compact"
                        onClick={() => void onResend(invite.invite_id)}
                        disabled={isBusy}
                      >
                        {busyAction === "resend" ? "Resending..." : "Resend"}
                      </button>
                    )}
                    {onRevoke && (
                      <button
                        className="btn btn-danger btn-compact"
                        onClick={() => void onRevoke(invite.invite_id)}
                        disabled={isBusy}
                      >
                        {busyAction === "revoke" ? "Revoking..." : "Revoke"}
                      </button>
                    )}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
