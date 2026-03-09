import type { Member } from "@/types/api";

export function MemberTable({ members }: { members: Member[] }) {
  return (
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
            <td>-</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
