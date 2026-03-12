"use client";

import { useEffect, useRef, useState } from "react";
import { inviteMember } from "@/lib/api";
import type { Invite, InviteMutationResult } from "@/types/api";

type InvitePanelResult = {
  invite: Invite | null;
  result: InviteMutationResult;
};

type InvitePanelProps = {
  orgId: string;
  onDone?: (payload: InvitePanelResult) => void;
};

export function InvitePanel({ orgId, onDone }: InvitePanelProps) {
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const successTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (successTimerRef.current) {
        window.clearTimeout(successTimerRef.current);
      }
    };
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;

    setSending(true);
    setError(null);
    setSuccess(false);
    if (successTimerRef.current) {
      window.clearTimeout(successTimerRef.current);
      successTimerRef.current = null;
    }

    try {
      const response = await inviteMember({ org_id: orgId, email: email.trim() });
      const invite = response.updated_record ?? response.invite ?? null;
      setEmail("");
      setSuccess(true);
      onDone?.({ invite, result: response });
      successTimerRef.current = window.setTimeout(() => {
        setSuccess(false);
        successTimerRef.current = null;
      }, 3000);
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
            autoComplete="email"
            inputMode="email"
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
