"use client";

import { useState } from "react";
import type { Member } from "@/types/api";

export function MemberTable({
  members,
  onKick,
}: {
  members: Member[];
  onKick?: (memberId: number) => Promise<void>;
}) {
  const [target, setTarget] = useState<Member | null>(null);
  const [kicking, setKicking] = useState(false);

  async function handleConfirmKick() {
    if (!target || !onKick) return;
    setKicking(true);
    try {
      await onKick(target.id);
    } finally {
      setKicking(false);
      setTarget(null);
    }
  }

  const statusClass = (s: string) =>
    s === "active" ? "status-active" :
    s === "pending" ? "status-pending" :
    s === "invited" ? "status-invited" :
    s === "removed" ? "status-removed" : "status-error";

  if (members.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">👥</div>
        <p>No members yet. Invite someone to get started!</p>
      </div>
    );
  }

  return (
    <>
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Join Date</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {members.map((m) => (
            <tr key={m.id}>
              <td>{m.name}</td>
              <td>{m.email}</td>
              <td style={{ textTransform: "capitalize" }}>{m.role}</td>
              <td>{m.invite_date ? new Date(m.invite_date).toLocaleDateString() : "—"}</td>
              <td>
                <span className={`status-badge ${statusClass(m.status)}`}>
                  <span className="status-dot" />
                  {m.status}
                </span>
              </td>
              <td>
                {m.role !== "owner" && (
                  <button className="btn btn-danger" onClick={() => setTarget(m)}>
                    Kick
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {target && (
        <div className="confirm-overlay" onClick={() => setTarget(null)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h4>⚠️ Confirm Kick</h4>
            <p>
              Are you sure you want to remove <strong>{target.name}</strong> ({target.email}) from
              this workspace? This action cannot be undone.
            </p>
            <div className="confirm-actions">
              <button className="btn btn-ghost" onClick={() => setTarget(null)}>
                Cancel
              </button>
              <button className="btn btn-danger" onClick={handleConfirmKick} disabled={kicking}>
                {kicking ? "Removing..." : "Confirm Kick"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
