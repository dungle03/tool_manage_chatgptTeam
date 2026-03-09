import { DashboardSummary } from "@/components/dashboard-summary";
import { WorkspaceCard } from "@/components/workspace-card";

export default function DashboardPage() {
  return (
    <main className="p-6 space-y-6">
      <DashboardSummary totalTeams={0} totalMembers={0} pendingInvites={0} syncErrors={0} />
      <WorkspaceCard title="No teams yet" members={0} memberLimit={0} status="synced" />
    </main>
  );
}
