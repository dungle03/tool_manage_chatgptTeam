type WorkspaceCardProps = {
  title: string;
  members: number;
  memberLimit: number;
  status: "synced" | "warning" | "error";
};

export function WorkspaceCard({ title, members, memberLimit, status }: WorkspaceCardProps) {
  return (
    <section>
      <h2>{title}</h2>
      <p>
        {members}/{memberLimit} members
      </p>
      <p>Status: {status}</p>
    </section>
  );
}
