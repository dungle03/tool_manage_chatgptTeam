type InviteItem = {
  id: number;
  email: string;
  status: string;
};

export function InviteList({ invites }: { invites: InviteItem[] }) {
  return (
    <ul>
      {invites.map((invite) => (
        <li key={invite.id}>
          {invite.email} - {invite.status}
        </li>
      ))}
    </ul>
  );
}
