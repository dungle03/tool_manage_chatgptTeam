"use client";

import { memo, useMemo, useState } from "react";
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

function rolePriority(role: string): number {
  switch (role.trim().toLowerCase()) {
    case "owner":
      return 0;
    case "admin":
      return 1;
    case "user":
    case "member":
    default:
      return 2;
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

function compareMembersByDisplayOrder(a: Member, b: Member): number {
  const joinedAtA = parseCreatedAtTimestamp(a.created_at ?? a.invite_date);
  const joinedAtB = parseCreatedAtTimestamp(b.created_at ?? b.invite_date);

  if (joinedAtA !== null && joinedAtB !== null && joinedAtA !== joinedAtB) {
    return joinedAtA - joinedAtB;
  }
  if (joinedAtA !== null && joinedAtB === null) {
    return -1;
  }
  if (joinedAtA === null && joinedAtB !== null) {
    return 1;
  }

  const roleDelta = rolePriority(a.role) - rolePriority(b.role);
  if (roleDelta !== 0) {
    return roleDelta;
  }

  const remoteIdA = a.remote_id ?? "";
  const remoteIdB = b.remote_id ?? "";
  if (remoteIdA !== remoteIdB) {
    return remoteIdA.localeCompare(remoteIdB);
  }

  if (a.email !== b.email) {
    return a.email.localeCompare(b.email);
  }

  return a.id - b.id;
}

type MemberTableProps = {
  members: Member[];
  busyMemberIds?: number[];
  onKick?: (memberId: number) => Promise<void>;
};

function MemberTableComponent({
  members,
  busyMemberIds = [],
  onKick,
}: MemberTableProps) {
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

  const sortedMembers = useMemo(
    () => [...members].sort(compareMembersByDisplayOrder),
    [members]
  );
  const busyMemberIdSet = useMemo(() => new Set(busyMemberIds), [busyMemberIds]);

  if (members.length === 0) {
    return (
      <div className="empty-state compact-empty-state">
        <div className="empty-icon">👥</div>
        <p>Workspace này chưa có thành viên nào.</p>
      </div>
    );
  }

  const eligibleMembers = sortedMembers
    .filter((member) => isActiveMember(member.status))
    .map((member) => {
      const joinedAtTimestamp = parseCreatedAtTimestamp(member.created_at ?? member.invite_date);
      if (joinedAtTimestamp === null) return null;
      return {
        id: member.id,
      };
    })
    .filter((member): member is { id: number } => member !== null);
  const overLimitMemberIds = new Set(eligibleMembers.slice(7).map((member) => member.id));

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
            {sortedMembers.map((member) => {
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
                        const isBusy = busyMemberIdSet.has(member.id);

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

export const MemberTable = memo(MemberTableComponent);
