"use client";

import { useState } from "react";
import { inviteMember } from "@/lib/api";

type InvitePanelProps = {
  orgId: string;
  onDone?: () => void;
};

export function InvitePanel({ orgId, onDone }: InvitePanelProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [sending, setSending] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setSending(true);
    setError(null);
    setSuccess(false);
    try {
      await inviteMember({ org_id: orgId, email: email.trim(), role });
      setEmail("");
      setSuccess(true);
      onDone?.();
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Có lỗi xảy ra";
      setError(msg);
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="invite-form" onSubmit={handleSubmit}>
      <div className="form-group" style={{ flex: 2 }}>
        <label className="form-label">Địa chỉ email</label>
        <input
          className="input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="user@company.com"
          type="email"
          required
        />
      </div>
      <div className="form-group">
        <label className="form-label">Vai trò</label>
        <select
          className="select"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        >
          <option value="member">Member</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <button
          className="btn btn-primary"
          type="submit"
          disabled={sending}
          style={{ whiteSpace: "nowrap" }}
        >
          {sending ? "Đang gửi..." : "📩 Gửi lời mời"}
        </button>
        {success && (
          <span
            style={{
              fontSize: "12px",
              color: "var(--success)",
              textAlign: "center",
            }}
          >
            ✅ Đã gửi!
          </span>
        )}
        {error && (
          <span
            style={{
              fontSize: "12px",
              color: "var(--danger)",
              textAlign: "center",
            }}
          >
            ⚠️ {error}
          </span>
        )}
      </div>
    </form>
  );
}
