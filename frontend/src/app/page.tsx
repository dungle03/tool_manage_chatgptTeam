"use client";

import { useEffect, useState, useCallback } from "react";
import { DashboardSummary } from "@/components/dashboard-summary";
import { WorkspaceCard } from "@/components/workspace-card";
import { MemberTable } from "@/components/member-table";
import { InvitePanel } from "@/components/invite-panel";
import { InviteList } from "@/components/invite-list";
import { ImportDialog } from "@/components/import-dialog";
import {
  getWorkspaces,
  getWorkspaceMembers,
  inviteMember,
  kickMember,
  listInvites,
} from "@/lib/api";
import type { Workspace, Member, Invite } from "@/types/api";

type WorkspaceState = {
  members: Member[];
  invites: Invite[];
  loadedMembers: boolean;
};

export default function DashboardPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [wsStates, setWsStates] = useState<Record<string, WorkspaceState>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showImport, setShowImport] = useState(false);

  const loadWorkspaces = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getWorkspaces();
      setWorkspaces(data);
    } catch {
      setError("Không thể tải danh sách workspace. Hãy kiểm tra backend đã chạy chưa.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

  async function loadWorkspaceData(orgId: string) {
    try {
      const [members, invites] = await Promise.all([
        getWorkspaceMembers(orgId),
        listInvites(orgId).catch(() => [] as Invite[]),
      ]);
      setWsStates((prev) => ({
        ...prev,
        [orgId]: { members, invites, loadedMembers: true },
      }));
    } catch {
      setError(`Không thể tải dữ liệu workspace ${orgId}`);
    }
  }

  async function handleInvite(orgId: string, email: string, role: string) {
    try {
      await inviteMember({ org_id: orgId, email, role });
      await loadWorkspaceData(orgId);
    } catch {
      setError("Không thể gửi lời mời.");
    }
  }

  async function handleKick(orgId: string, memberId: number) {
    try {
      await kickMember({ org_id: orgId, member_id: memberId });
      await loadWorkspaceData(orgId);
    } catch {
      setError("Không thể xóa thành viên.");
    }
  }

  // Totals for summary
  const totalMembers = Object.values(wsStates).reduce(
    (sum, s) => sum + s.members.filter((m) => m.status === "active").length,
    0
  );
  const totalPending = Object.values(wsStates).reduce(
    (sum, s) => sum + s.invites.filter((i) => i.status === "pending").length,
    0
  );

  return (
    <main className="dashboard-layout">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">🏢 ChatGPT Team Manager</h1>
          <p className="dashboard-subtitle">Quản lý workspace và thành viên</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowImport(true)}
          id="import-team-btn"
        >
          + Thêm Team
        </button>
      </div>


      <DashboardSummary
        totalTeams={workspaces.length}
        totalMembers={totalMembers}
        pendingInvites={totalPending}
        syncErrors={0}
      />

      {error && (
        <div role="alert" aria-live="polite" className="error-banner">
          {error}
          <button onClick={() => setError(null)} className="error-dismiss">
            ✕
          </button>
        </div>
      )}

      {loading && (
        <div className="loading-state">
          <div className="loading-spinner" />
          <span>Đang tải danh sách workspace...</span>
        </div>
      )}

      {!loading && workspaces.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">🏢</div>
          <p>Chưa có workspace nào. Hãy import Access Token từ ChatGPT để bắt đầu.</p>
        </div>
      )}

      {/* Accordion Workspace List */}
      <div className="workspace-list">
        {workspaces.map((ws) => {
          const state = wsStates[ws.org_id] ?? { members: [], invites: [], loadedMembers: false };
          const wsStatus =
            ws.status === "live" ? "synced" :
            ws.status === "error" ? "error" : "warning";

          return (
            <WorkspaceCard
              key={ws.org_id}
              title={ws.name}
              members={ws.member_count}
              memberLimit={ws.member_limit}
              status={wsStatus}
              lastSync={ws.last_sync}
              onSync={() => loadWorkspaceData(ws.org_id)}
              onInvite={() => {/* open invite panel */}}
              expandedContent={
                <div className="workspace-detail">
                  {!state.loadedMembers ? (
                    <button
                      className="btn btn-secondary"
                      onClick={() => loadWorkspaceData(ws.org_id)}
                    >
                      ↺ Tải dữ liệu
                    </button>
                  ) : (
                    <>
                      <MemberTable
                        members={state.members}
                        onKick={(memberId) => handleKick(ws.org_id, memberId)}
                      />

                      <div className="section-panel">
                        <h3 className="section-title">Mời thành viên mới</h3>
                        <InvitePanel onInvite={(email, role) => handleInvite(ws.org_id, email, role)} />
                      </div>

                      {state.invites.length > 0 && (
                        <div className="section-panel">
                          <h3 className="section-title">Lời mời đang chờ ({state.invites.length})</h3>
                          <InviteList invites={state.invites} />
                        </div>
                      )}
                    </>
                  )}
                </div>
              }
            />
          );
        })}
      </div>

      {showImport && (
        <ImportDialog
          onClose={() => setShowImport(false)}
          onImported={(orgId) => {
            setShowImport(false);
            loadWorkspaces();
          }}
        />
      )}
    </main>
  );
}
