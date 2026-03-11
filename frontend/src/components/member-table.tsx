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

function isActiveMember(status: string): boolean {
  return status.trim().toLowerCase() === "active";
}

function parseCreatedAtTimestamp(createdAt: string | null): number | null {
  if (!createdAt) return null;
  const timestamp = Date.parse(createdAt);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function formatJoinDate(createdAt: string | null, inviteDate: string | null): string {
  const source = createdAt || inviteDate;
  if (!source) return "Tham gia: Chưa rõ";

  const date = new Date(source);
  if (Number.isNaN(date.getTime())) {
    return "Tham gia: Chưa rõ";
  }

  const day = String(date.getUTCDate()).padStart(2, "0");
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const year = date.getUTCFullYear();
  return `Tham gia: ${day}/${month}/${year}`;
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

  const eligibleMembers = members
    .map((member) => {
      if (!isActiveMember(member.status)) return null;
      const createdAtTimestamp = parseCreatedAtTimestamp(member.created_at);
      if (createdAtTimestamp === null) return null;
      return {
        id: member.id,
        remoteId: member.remote_id ?? "",
        createdAtTimestamp,
      };
    })
    .filter((member): member is { id: number; remoteId: string; createdAtTimestamp: number } => member !== null)
    .sort((a, b) => {
      if (a.createdAtTimestamp !== b.createdAtTimestamp) {
        return a.createdAtTimestamp - b.createdAtTimestamp;
      }
      if (a.remoteId !== b.remoteId) {
        return a.remoteId.localeCompare(b.remoteId);
      }
      return a.id - b.id;
    });
  const overLimitMemberIds = new Set(eligibleMembers.slice(5).map((member) => member.id));

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
                <tr key={member.id} className={overLimitMemberIds.has(member.id) ? "member-overlimit-row" : undefined}>
                  <td>
                    <div className="member-cell">
                      <div className="member-avatar">{initialsOf(member.name, member.email)}</div>
                      <div className="member-info">
                        <div className="member-name">{displayName}</div>
                        <div className="member-subtle">
                          {formatJoinDate(member.created_at, member.invite_date)}
                        </div>
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
                    <div className="table-action-content">
                      {isOwner || !onKick ? (
                        <span className="action-pill action-pill-protected">Protected</span>
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
                    </div>
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
