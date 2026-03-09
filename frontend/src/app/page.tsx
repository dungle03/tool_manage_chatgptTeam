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
import type { Workspace, Member, Invite } from "@/types/api";

export default function DashboardPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<string | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorkspaces();
  }, []);

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
    } catch {
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
      /* ignored */
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
    <main className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Workspace Manager</h1>
          <div className="subtitle">Manage your ChatGPT Team workspaces</div>
        </div>
      </div>

      <DashboardSummary
        totalTeams={workspaces.length}
        totalMembers={activeMembers.length}
        pendingInvites={pendingInviteCount}
        syncErrors={0}
      />

      {error && (
        <div className="alert alert-error">
          <span>⚠️ {error}</span>
          <button className="alert-dismiss" onClick={() => setError(null)}>
            ✕
          </button>
        </div>
      )}

      {loading && (
        <div className="loading">
          <div className="spinner" />
          <p style={{ marginTop: 12 }}>Loading workspaces...</p>
        </div>
      )}

      {!loading && workspaces.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">🏢</div>
          <p>No workspaces yet. Start the backend and seed some data.</p>
        </div>
      )}

      {workspaces.length > 0 && (
        <div className="workspaces-grid">
          {workspaces.map((ws) => (
            <div key={ws.org_id} onClick={() => setSelectedOrg(ws.org_id)}>
              <WorkspaceCard
                title={ws.name}
                members={activeMembers.length}
                memberLimit={ws.member_limit}
                status="synced"
                selected={ws.org_id === selectedOrg}
              />
            </div>
          ))}
        </div>
      )}

      {selectedOrg && selectedWorkspace && (
        <>
          <div className="section-panel">
            <h2>👥 {selectedWorkspace.name} — Members</h2>
            <MemberTable members={members} onKick={handleKick} />
          </div>

          <div className="section-panel">
            <h3>📩 Invite New Member</h3>
            <InvitePanel onInvite={handleInvite} />
          </div>

          {invites.length > 0 && (
            <div className="section-panel">
              <h3>📋 Pending Invites</h3>
              <InviteList invites={invites} />
            </div>
          )}
        </>
      )}
    </main>
  );
}
