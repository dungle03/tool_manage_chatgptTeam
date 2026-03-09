"use client";

import { useState } from "react";
import type { Member } from "@/types/api";

function roleLabel(role: string): string {
  switch (role.toLowerCase()) {
    case "owner": return "👑 Owner";
    case "admin": return "🛡️ Admin";
    case "pending": return "⏳ Pending";
    default: return "👤 User";
  }
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  return `${d.getDate()}/${d.getMonth() + 1}`;
}

export function MemberTable({
  members,
  onKick,
  onCancelInvite,
}: {
  members: Member[];
  onKick?: (memberId: number) => Promise<void>;
  onCancelInvite?: (email: string) => Promise<void>;
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [target, setTarget] = useState<Member | null>(null);
  const [kicking, setKicking] = useState(false);

  function toggleAll() {
    if (selected.size === members.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(members.map((m) => m.id)));
    }
  }

  function toggleRow(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

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
      <div className="empty-state">
        <div className="empty-icon">👥</div>
        <p>Chưa có thành viên nào. Mời ai đó để bắt đầu!</p>
      </div>
    );
  }

  return (
    <>
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: "36px" }}>
              <input
                type="checkbox"
                checked={selected.size === members.length}
                onChange={toggleAll}
                aria-label="Chọn tất cả"
              />
            </th>
            <th style={{ width: "36px" }}>#</th>
            <th>EMAIL</th>
            <th>TÊN TÀI KHOẢN</th>
            <th>VAI TRÒ</th>
            <th>NGÀY MỜI</th>
            <th>HÀNH ĐỘNG</th>
          </tr>
        </thead>
        <tbody>
          {members.map((m, idx) => {
            const isPending = m.status === "pending" || m.status === "invited";
            const isOwner = m.role.toLowerCase() === "owner";

            return (
              <tr key={m.id} className={selected.has(m.id) ? "selected-row" : ""}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(m.id)}
                    onChange={() => toggleRow(m.id)}
                    aria-label={`Chọn ${m.email}`}
                  />
                </td>
                <td style={{ opacity: 0.5, fontSize: "12px" }}>{idx + 1}</td>
                <td>
                  <span
                    style={{
                      color: isPending ? "var(--text-secondary)" : "var(--accent)",
                      fontSize: "13px",
                    }}
                  >
                    {m.email}
                  </span>
                </td>
                <td style={{ fontSize: "13px" }}>{m.name || "—"}</td>
                <td>
                  <span style={{ fontSize: "13px" }}>
                    {isPending ? "⏳ Pending" : roleLabel(m.role)}
                  </span>
                </td>
                <td style={{ fontSize: "12px", opacity: 0.7 }}>
                  {formatDate(m.invite_date)}
                </td>
                <td>
                  <div style={{ display: "flex", gap: "6px" }}>
                    {isPending && onCancelInvite && (
                      <button
                        className="btn btn-danger"
                        style={{ fontSize: "12px", padding: "3px 10px" }}
                        onClick={() => onCancelInvite(m.email)}
                      >
                        Hủy
                      </button>
                    )}
                    {!isPending && !isOwner && onKick && (
                      <button
                        className="btn btn-danger"
                        style={{ fontSize: "12px", padding: "3px 10px" }}
                        onClick={() => setTarget(m)}
                      >
                        Xóa
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Confirm Modal */}
      {target && (
        <div className="confirm-overlay" onClick={() => setTarget(null)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h4>⚠️ Xác nhận xóa thành viên</h4>
            <p>
              Bạn có chắc muốn xóa <strong>{target.name || target.email}</strong> (
              {target.email}) khỏi workspace? Hành động này không thể hoàn tác.
            </p>
            <div className="confirm-actions">
              <button className="btn btn-ghost" onClick={() => setTarget(null)}>
                Hủy
              </button>
              <button className="btn btn-danger" onClick={handleConfirmKick} disabled={kicking}>
                {kicking ? "Đang xóa..." : "Xác nhận xóa"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
