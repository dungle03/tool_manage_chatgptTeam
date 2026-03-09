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
    <form className="invite-form-card" onSubmit={handleSubmit}>
      <div className="section-heading-row compact-heading-row">
        <div>
          <h3 className="section-heading">Invite a new member</h3>
          <p className="section-description">Nhập email và phân quyền trước khi gửi lời mời.</p>
        </div>
      </div>

      <div className="invite-form-grid">
        <div className="form-group">
          <label className="form-label">Email</label>
          <input
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@company.com"
            type="email"
            required
            id={`invite-email-${orgId}`}
          />
        </div>

        <div className="form-group form-group-narrow">
          <label className="form-label">Role</label>
          <select className="select" value={role} onChange={(e) => setRole(e.target.value)} id={`invite-role-${orgId}`}>
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        <div className="invite-submit-wrap">
          <button className="btn btn-primary invite-submit-btn" type="submit" disabled={sending} id={`invite-submit-${orgId}`}>
            {sending ? "Sending..." : "Send invite"}
          </button>
        </div>
      </div>

      {success && <div className="inline-feedback success-feedback">Đã gửi lời mời thành công.</div>}
      {error && <div className="inline-feedback error-feedback">{error}</div>}
    </form>
  );
}
