"use client";

import { useState } from "react";

export function InvitePanel({ onInvite }: { onInvite: (email: string, role: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        await onInvite(email, role);
      }}
      className="space-y-2"
    >
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <select value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="member">member</option>
        <option value="admin">admin</option>
      </select>
      <button type="submit">Send Invite</button>
    </form>
  );
}
