"use client";

import { useState } from "react";

export function InvitePanel({ onInvite }: { onInvite: (email: string, role: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [sending, setSending] = useState(false);

  return (
    <form
      className="invite-form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (!email.trim()) return;
        setSending(true);
        try {
          await onInvite(email, role);
          setEmail("");
        } finally {
          setSending(false);
        }
      }}
    >
      <div className="form-group" style={{ flex: 2 }}>
        <label className="form-label">Email address</label>
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
        <label className="form-label">Role</label>
        <select className="select" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="member">Member</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <button className="btn btn-primary" type="submit" disabled={sending}>
        {sending ? "Sending..." : "📩 Send Invite"}
      </button>
    </form>
  );
}
