"use client";

import { useState } from "react";
import type { Member } from "@/types/api";

export function MemberTable({ members }: { members: Member[] }) {
  const [target, setTarget] = useState<Member | null>(null);

  return (
    <div>
      <table className="w-full">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Join Date</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {members.map((m) => (
            <tr key={m.id}>
              <td>{m.name}</td>
              <td>{m.email}</td>
              <td>{m.invite_date ?? "-"}</td>
              <td>{m.status}</td>
              <td>
                <button onClick={() => setTarget(m)}>Kick</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {target && (
        <div>
          <p>Confirm kick member</p>
          <p>{target.email}</p>
          <button onClick={() => setTarget(null)}>Cancel</button>
          <button>Confirm</button>
        </div>
      )}
    </div>
  );
}
