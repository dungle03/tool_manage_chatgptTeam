"use client";

import { useState } from "react";
import type { Member } from "@/types/api";

function roleTone(role: string) {
  switch (role.toLowerCase()) {
    case "owner":
      return { label: "Owner", className: "role-owner" };
    case "admin":
      return { label: "Admin", className: "role-admin" };
    case "user":
    case "member":
    default:
      return { label: "User", className: "role-user" };
  }
}

function initialsOf(name: string, email: string): string {
  const source = name?.trim() || email.trim();
  return (
    source
      .split(/[\s@._-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "U"
  );
}

export function MemberTable({
  members,
  busyMemberIds = [],
  onKick,
}: {
  members: Member[];
  busyMemberIds?: number[];
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

  if (members.length === 0) {
    return (
      <div className="empty-state compact-empty-state">
        <div className="empty-icon">👥</div>
        <p>Workspace này chưa có thành viên nào.</p>
      </div>
    );
  }

  return (
    <>
      <div className="table-shell">
        <div className="section-heading-row">
          <div>
            <h3 className="section-heading">Members</h3>
            <p className="section-description">Danh sách thành viên hiện tại của workspace.</p>
          </div>
          <div className="section-count">{members.length} người</div>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Member</th>
              <th>Email</th>
              <th>Role</th>
              <th className="table-action-head">Action</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => {
              const isOwner = member.role.toLowerCase() === "owner";
              const role = roleTone(member.role);
              const displayName = member.name || "No name";

              return (
                <tr key={member.id}>
                  <td>
                    <div className="member-cell">
                      <div className="member-avatar">{initialsOf(member.name, member.email)}</div>
                      <div className="member-info">
                        <div className="member-name">{displayName}</div>
                        <div className="member-subtle">ID: {member.remote_id || member.id}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="member-email">{member.email}</span>
                  </td>
                  <td>
                    <span className={`role-pill ${role.className}`}>{role.label}</span>
                  </td>
                  <td className="table-action-cell">
                    {isOwner || !onKick ? (
                      <span className="muted-inline">Protected</span>
                    ) : (() => {
                      const isBusy = busyMemberIds.includes(member.id);

                      return (
                        <button
                          className={`action-btn action-btn-kick${isBusy ? " action-btn-loading" : ""}`}
                          onClick={() => setTarget(member)}
                          disabled={isBusy}
                        >
                          {isBusy ? "Removing..." : "Kick"}
                        </button>
                      );
                    })()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {target && (
        <div className="confirm-overlay" onClick={() => setTarget(null)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h4>Xác nhận xóa thành viên</h4>
            <p>
              Bạn có chắc muốn xóa <strong>{target.name || target.email}</strong> khỏi workspace không?
            </p>
            <div className="confirm-actions">
              <button className="btn btn-ghost" onClick={() => setTarget(null)}>
                Hủy
              </button>
              <button className="btn btn-danger" onClick={handleConfirmKick} disabled={kicking}>
                {kicking ? "Đang xóa..." : "Xóa thành viên"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
