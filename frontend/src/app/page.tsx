"use client";

import { useEffect, useState } from "react";
import { DashboardSummary } from "@/components/dashboard-summary";
import { WorkspaceCard } from "@/components/workspace-card";
import { MemberTable } from "@/components/member-table";
import { InvitePanel } from "@/components/invite-panel";
import { InviteList } from "@/components/invite-list";
import {
  getWorkspaces,
  getWorkspaceMembers,
  inviteMember,
  kickMember,
  listInvites,
} from "@/lib/api";
import type { Workspace, Member } from "@/types/api";
import type { Invite } from "@/types/api";

export default function DashboardPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<string | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Load workspaces on mount
  useEffect(() => {
    loadWorkspaces();
  }, []);

  // Load members + invites when workspace selected
  useEffect(() => {
    if (selectedOrg) {
      loadMembers(selectedOrg);
      loadInvites(selectedOrg);
    }
  }, [selectedOrg]);

  async function loadWorkspaces() {
    try {
      setLoading(true);
      setError(null);
      const data = await getWorkspaces();
      setWorkspaces(data);
      if (data.length > 0 && !selectedOrg) {
        setSelectedOrg(data[0].org_id);
      }
    } catch (err) {
      setError("Failed to load workspaces");
    } finally {
      setLoading(false);
    }
  }

  async function loadMembers(orgId: string) {
    try {
      const data = await getWorkspaceMembers(orgId);
      setMembers(data.filter((m: Member) => m.status !== "removed"));
    } catch {
      setError("Failed to load members");
    }
  }

  async function loadInvites(orgId: string) {
    try {
      const data = await listInvites(orgId);
      setInvites(data);
    } catch {
      /* ignored - invites are optional */
    }
  }

  async function handleInvite(email: string, role: string) {
    if (!selectedOrg) return;
    try {
      await inviteMember({ org_id: selectedOrg, email, role });
      await loadInvites(selectedOrg);
    } catch {
      setError("Failed to send invite");
    }
  }

  async function handleKick(memberId: number) {
    if (!selectedOrg) return;
    try {
      await kickMember({ org_id: selectedOrg, member_id: memberId });
      await loadMembers(selectedOrg);
    } catch {
      setError("Failed to kick member");
    }
  }

  const activeMembers = members.filter((m) => m.status === "active");
  const pendingInviteCount = invites.filter((i) => i.status === "pending").length;
  const selectedWorkspace = workspaces.find((w) => w.org_id === selectedOrg);

  return (
    <main className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Workspace Manager</h1>

      <DashboardSummary
        totalTeams={workspaces.length}
        totalMembers={activeMembers.length}
        pendingInvites={pendingInviteCount}
        syncErrors={0}
      />

      {error && (
        <div role="alert" aria-live="polite" className="text-sm text-red-600 p-3 bg-red-50 rounded">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}

      {loading && <p>Loading workspaces...</p>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {workspaces.map((ws) => (
          <div key={ws.org_id} onClick={() => setSelectedOrg(ws.org_id)} className="cursor-pointer">
            <WorkspaceCard
              title={ws.name}
              members={activeMembers.length}
              memberLimit={ws.member_limit}
              status={ws.org_id === selectedOrg ? "synced" : "synced"}
            />
          </div>
        ))}
      </div>

      {selectedOrg && selectedWorkspace && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">{selectedWorkspace.name} - Members</h2>

          <MemberTable members={members} onKick={handleKick} />

          <h3 className="text-lg font-semibold">Invite New Member</h3>
          <InvitePanel onInvite={handleInvite} />

          {invites.length > 0 && (
            <>
              <h3 className="text-lg font-semibold">Pending Invites</h3>
              <InviteList invites={invites} />
            </>
          )}
        </section>
      )}
    </main>
  );
}
