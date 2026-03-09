"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { DashboardSummary } from "@/components/dashboard-summary";
import { WorkspaceCard } from "@/components/workspace-card";
import { MemberTable } from "@/components/member-table";
import { InvitePanel } from "@/components/invite-panel";
import { InviteList } from "@/components/invite-list";
import { ImportDialog } from "@/components/import-dialog";
import {
  getWorkspaces,
  getWorkspaceMembers,
  kickMember,
  listInvites,
  syncWorkspace,
  deleteWorkspace,
} from "@/lib/api";
import type { Workspace, Member, Invite } from "@/types/api";

type WorkspaceState = {
  members: Member[];
  invites: Invite[];
  loadedMembers: boolean;
  syncing: boolean;
  showInviteForm: boolean;
};

const DEFAULT_WS_STATE: WorkspaceState = {
  members: [],
  invites: [],
  loadedMembers: false,
  syncing: false,
  showInviteForm: false,
};

export default function DashboardPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [wsStates, setWsStates] = useState<Record<string, WorkspaceState>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showImport, setShowImport] = useState(false);
  const [deletingWs, setDeletingWs] = useState<Workspace | null>(null);
  const [deleting, setDeleting] = useState(false);
  const inflightMemberLoads = useRef(new Map<string, Promise<void>>());

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

  function updateWsState(orgId: string, patch: Partial<WorkspaceState>) {
    setWsStates((prev) => ({
      ...prev,
      [orgId]: { ...(prev[orgId] ?? DEFAULT_WS_STATE), ...patch },
    }));
  }

  async function loadMembers(orgId: string) {
    const existingRequest = inflightMemberLoads.current.get(orgId);
    if (existingRequest) {
      return existingRequest;
    }

    const request = (async () => {
      updateWsState(orgId, { syncing: true });
      try {
        const [members, invites] = await Promise.all([
          getWorkspaceMembers(orgId),
          listInvites(orgId).catch(() => [] as Invite[]),
        ]);
        updateWsState(orgId, { members, invites, loadedMembers: true });
      } catch {
        setError(`Không thể tải dữ liệu workspace ${orgId}`);
      } finally {
        updateWsState(orgId, { syncing: false });
        inflightMemberLoads.current.delete(orgId);
      }
    })();

    inflightMemberLoads.current.set(orgId, request);
    return request;
  }

  // Nút ↺ Sync — gọi real API ChatGPT, sau đó reload
  async function handleSync(orgId: string) {
    updateWsState(orgId, { syncing: true });
    try {
      await syncWorkspace(orgId);
      await loadMembers(orgId);
      await loadWorkspaces(); // cập nhật member_count
    } catch {
      setError(`Sync thất bại cho workspace ${orgId}. Token có thể đã hết hạn.`);
      updateWsState(orgId, { syncing: false });
    }
  }

  async function handleKick(orgId: string, memberId: number) {
    try {
      await kickMember({ org_id: orgId, member_id: memberId });
      await loadMembers(orgId);
    } catch {
      setError("Không thể xóa thành viên.");
    }
  }

  async function handleConfirmDelete() {
    if (!deletingWs) return;
    setDeleting(true);
    try {
      await deleteWorkspace(deletingWs.org_id);
      await loadWorkspaces();
      setDeletingWs(null);
    } catch {
      setError(`Không thể xóa workspace ${deletingWs.name}`);
    } finally {
      setDeleting(false);
    }
  }

  // Tính tổng cho DashboardSummary
  const totalMembers = workspaces.reduce((s, w) => s + (w.member_count ?? 0), 0);
  const totalPending = Object.values(wsStates).reduce(
    (sum, s) => sum + s.invites.filter((i) => i.status === "pending").length,
    0
  );

  return (
    <main className="dashboard-layout">
      <div className="dashboard-header">
        <div className="dashboard-header-copy">
          <span className="eyebrow">Workspace control center</span>
          <h1 className="dashboard-title">ChatGPT Team Manager</h1>
          <p className="dashboard-subtitle">
            Theo dõi workspace, quản lý thành viên và xử lý lời mời trong một dashboard rõ ràng hơn.
          </p>
        </div>
        <div className="dashboard-header-actions">
          <button
            className="btn btn-primary"
            onClick={() => setShowImport(true)}
            id="import-team-btn"
          >
            + Import Team
          </button>
        </div>
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
          <button onClick={() => setError(null)} className="error-dismiss">✕</button>
        </div>
      )}

      {loading && (
        <div className="loading-state">
          <div className="loading-spinner" />
          <span>Đang tải danh sách workspace...</span>
        </div>
      )}

      {!loading && workspaces.length === 0 && (
        <div className="empty-state hero-empty-state">
          <div className="empty-icon">◫</div>
          <div className="empty-copy">
            <h3>Chưa có workspace nào</h3>
            <p>
              Import team đầu tiên để bắt đầu quản lý member, lời mời và trạng thái đồng bộ từ ChatGPT.
            </p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowImport(true)}>
            Import workspace đầu tiên
          </button>
        </div>
      )}

      {/* Accordion Workspace List */}
      <div className="workspace-list">
        {workspaces.map((ws) => {
          const state = wsStates[ws.org_id] ?? DEFAULT_WS_STATE;
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
              syncing={state.syncing}
              onSync={() => handleSync(ws.org_id)}
              onDelete={() => setDeletingWs(ws)}
              onInvite={() => {
                updateWsState(ws.org_id, {
                  showInviteForm: !state.showInviteForm,
                  loadedMembers: state.loadedMembers,
                });
              }}
              onExpandedChange={(expanded) => {
                if (expanded && !state.loadedMembers && (Boolean(ws.last_sync) || ws.member_count > 0) && !state.syncing) {
                  void loadMembers(ws.org_id);
                }
              }}
              expandedContent={
                <div className="workspace-detail">
                  {!state.loadedMembers ? (
                    <div className="section-panel section-panel-center">
                      <div className="section-heading-row compact-heading-row">
                        <div>
                          <h3 className="section-heading">
                            {ws.last_sync || ws.member_count > 0 ? "Đang tải dữ liệu workspace" : "Workspace data chưa được tải"}
                          </h3>
                          <p className="section-description">
                            {ws.last_sync || ws.member_count > 0
                              ? "Đang đọc dữ liệu local đã sync trước đó để hiển thị members và invites."
                              : "Đồng bộ ngay để lấy danh sách thành viên và lời mời mới nhất từ ChatGPT."}
                          </p>
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                        {ws.last_sync || ws.member_count > 0 ? (
                          <>
                            <div className="loading-spinner" />
                            <span className="workspace-helper-copy">Đang tải dữ liệu cục bộ của workspace...</span>
                          </>
                        ) : (
                          <>
                            <button
                              className="btn btn-primary"
                              onClick={() => handleSync(ws.org_id)}
                              disabled={state.syncing}
                            >
                              {state.syncing ? "Đang sync..." : "Sync workspace"}
                            </button>
                            <span className="workspace-helper-copy">Workspace này chưa có dữ liệu cục bộ, hãy sync lần đầu để tải members và invites.</span>
                          </>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="workspace-sections-grid">
                      <div className="workspace-primary-column">
                        <MemberTable
                          members={state.members}
                          onKick={ws.can_manage_members ? (memberId) => handleKick(ws.org_id, memberId) : undefined}
                        />
                      </div>

                      <div className="workspace-side-column">
                        {state.showInviteForm && (
                          <div className="section-panel invite-section-panel">
                            <InvitePanel
                              orgId={ws.org_id}
                              onDone={() => loadMembers(ws.org_id)}
                            />
                          </div>
                        )}

                        {state.invites.length > 0 && (
                          <div className="section-panel invite-section-panel">
                            <InviteList invites={state.invites} />
                          </div>
                        )}
                      </div>
                    </div>
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
          onImported={() => {
            setShowImport(false);
            loadWorkspaces();
          }}
        />
      )}

      {/* Delete Workspace Confirmation Modal */}
      {deletingWs && (
        <div className="confirm-overlay" onClick={() => !deleting && setDeletingWs(null)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h4>⚠️ Xác nhận xóa Workspace</h4>
            <p>
              Bạn có chắc muốn xóa <strong>{deletingWs.name}</strong> không? Các dữ liệu về member
              trong tool sẽ bị xóa (không ảnh hưởng tới tài khoản gốc trên ChatGPT).
            </p>
            <div className="confirm-actions">
              <button 
                className="btn btn-ghost" 
                onClick={() => setDeletingWs(null)}
                disabled={deleting}
              >
                Hủy
              </button>
              <button 
                className="btn btn-danger" 
                onClick={handleConfirmDelete}
                disabled={deleting}
              >
                {deleting ? "Đang xóa..." : "Xác nhận xóa"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
