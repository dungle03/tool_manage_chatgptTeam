"use client";

import { useState } from "react";
import { inviteMember } from "@/lib/api";

type InvitePanelProps = {
  orgId: string;
  onDone?: () => void;
};

export function InvitePanel({ orgId, onDone }: InvitePanelProps) {
  const [email, setEmail] = useState("");
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
      await inviteMember({ org_id: orgId, email: email.trim() });
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
      <div className="section-heading-row compact-heading-row invite-panel-header">
        <div>
          <h3 className="section-heading">Invite a new member</h3>
          <p className="section-description">Nhập email công việc và chọn quyền trước khi gửi lời mời vào workspace.</p>
        </div>
      </div>

      <div className="invite-form-grid invite-form-grid-single">
        <div className="form-group invite-form-group-primary">
          <label className="form-label" htmlFor={`invite-email-${orgId}`}>Email</label>
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
      </div>

      <div className="invite-form-actions">
        <p className="invite-form-note">Chỉ cần nhập email để gửi lời mời. Thành viên mới sẽ vào danh sách pending invites ngay sau khi gửi.</p>
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
