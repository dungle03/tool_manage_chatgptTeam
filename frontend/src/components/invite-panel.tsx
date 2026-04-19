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

const EMAIL_LINE_SPLIT_REGEX = /\r?\n/;
const SIMPLE_EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/i;

function parseEmailLines(raw: string): string[] {
  const seen = new Set<string>();
  const emails: string[] = [];

  for (const line of raw.split(EMAIL_LINE_SPLIT_REGEX)) {
    const normalized = line.trim().toLowerCase();
    if (!normalized || seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    emails.push(normalized);
  }

  return emails;
}

export function InvitePanel({ orgId, onDone }: InvitePanelProps) {
  const [emailInput, setEmailInput] = useState("");
  const [sending, setSending] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
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

    const emails = parseEmailLines(emailInput);
    if (emails.length === 0) {
      return;
    }

    const invalidEmails = emails.filter((email) => !SIMPLE_EMAIL_REGEX.test(email));
    if (invalidEmails.length > 0) {
      setError(`Email không hợp lệ: ${invalidEmails.join(", ")}`);
      setSuccessMessage(null);
      return;
    }

    setSending(true);
    setError(null);
    setSuccessMessage(null);
    if (successTimerRef.current) {
      window.clearTimeout(successTimerRef.current);
      successTimerRef.current = null;
    }

    const failures: string[] = [];
    let successCount = 0;

    try {
      for (const email of emails) {
        try {
          const response = await inviteMember({ org_id: orgId, email });
          const invite = response.updated_record ?? response.invite ?? null;
          successCount += 1;
          onDone?.({ invite, result: response });
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : "Có lỗi xảy ra";
          failures.push(`${email} (${msg})`);
        }
      }

      if (successCount > 0) {
        setEmailInput("");
      }

      if (successCount > 0 && failures.length === 0) {
        setSuccessMessage(
          successCount === 1
            ? "Đã gửi lời mời thành công."
            : `Đã gửi thành công ${successCount} lời mời.`
        );
      } else if (successCount > 0) {
        setSuccessMessage(`Đã gửi thành công ${successCount}/${emails.length} lời mời.`);
        setError(`Không gửi được ${failures.length} email: ${failures.join("; ")}`);
      } else {
        setError(`Không gửi được email nào: ${failures.join("; ")}`);
      }

      if (successCount > 0) {
        successTimerRef.current = window.setTimeout(() => {
          setSuccessMessage(null);
          successTimerRef.current = null;
        }, 4000);
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="invite-form-card" onSubmit={handleSubmit}>
      <div className="section-heading-row compact-heading-row invite-panel-header">
        <div>
          <h3 className="section-heading">Invite a new member</h3>
          <p className="section-description">Nhập một hoặc nhiều email, mỗi email trên một dòng, rồi gửi lời mời vào workspace.</p>
        </div>
      </div>

      <div className="invite-form-grid invite-form-grid-single">
        <div className="form-group invite-form-group-primary">
          <label className="form-label" htmlFor={`invite-email-${orgId}`}>Danh sách email</label>
          <textarea
            className="input"
            value={emailInput}
            onChange={(e) => setEmailInput(e.target.value)}
            placeholder={"name@company.com\nname2@company.com\nname3@company.com"}
            required
            id={`invite-email-${orgId}`}
            autoComplete="off"
            rows={4}
            spellCheck={false}
          />
        </div>
      </div>

      <div className="invite-form-actions">
        <p className="invite-form-note">Mỗi email một dòng. Hệ thống sẽ tự bỏ dòng trống, lọc email trùng và gửi lần lượt bằng flow invite hiện tại.</p>
        <div className="invite-submit-wrap">
          <button className="btn btn-primary invite-submit-btn" type="submit" disabled={sending} id={`invite-submit-${orgId}`}>
            {sending ? "Sending..." : "Send invite"}
          </button>
        </div>
      </div>

      {successMessage && <div className="inline-feedback success-feedback">{successMessage}</div>}
      {error && <div className="inline-feedback error-feedback">{error}</div>}
    </form>
  );
}
