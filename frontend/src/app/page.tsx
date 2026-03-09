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
  resendInvite,
  cancelInvite,
} from "@/lib/api";
import type { Workspace, Member, Invite } from "@/types/api";

type WorkspaceState = {
  members: Member[];
  invites: Invite[];
  loadedMembers: boolean;
  syncing: boolean;
  busyMemberIds: number[];
  inviteActionState: Record<string, "resend" | "revoke">;
};

type ToastState = {
  id: number;
  title: string;
  message: string;
  tone: "success" | "error" | "info";
};

const DEFAULT_WS_STATE: WorkspaceState = {
  members: [],
  invites: [],
  loadedMembers: false,
  syncing: false,
  busyMemberIds: [],
  inviteActionState: {},
};

export default function DashboardPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [wsStates, setWsStates] = useState<Record<string, WorkspaceState>>({});
  const [toasts, setToasts] = useState<ToastState[]>([]);
  const [loading, setLoading] = useState(true);
  const [showImport, setShowImport] = useState(false);
  const [deletingWs, setDeletingWs] = useState<Workspace | null>(null);
  const [deleting, setDeleting] = useState(false);
  const inflightMemberLoads = useRef(new Map<string, Promise<void>>());

  const loadWorkspaces = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getWorkspaces();
      setWorkspaces(data);
    } catch {
      showToast("Không thể tải workspace", "Hãy kiểm tra backend đang chạy và thử tải lại dashboard.", "error");
    } finally {
      setLoading(false);
    }
  }, []);


  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

  function updateWsState(orgId: string, patch: Partial<WorkspaceState> | ((current: WorkspaceState) => Partial<WorkspaceState>)) {
    setWsStates((prev) => {
      const current = prev[orgId] ?? DEFAULT_WS_STATE;
      const nextPatch = typeof patch === "function" ? patch(current) : patch;

      return {
        ...prev,
        [orgId]: { ...current, ...nextPatch },
      };
    });
  }

  function showToast(
    title: string,
    message: string,
    tone: ToastState["tone"] = "info"
  ) {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => [...prev, { id, title, message, tone }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 3600);
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
        showToast("Không thể tải dữ liệu workspace", `Workspace ${orgId} hiện chưa đọc được members hoặc invites.`, "error");
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
      await loadWorkspaces();
      showToast("Đồng bộ hoàn tất", `Workspace ${orgId} đã được cập nhật dữ liệu mới nhất.`, "success");
    } catch {
      showToast("Sync thất bại", `Workspace ${orgId} chưa thể đồng bộ. Token có thể đã hết hạn.`, "error");
      updateWsState(orgId, { syncing: false });
    }
  }

  async function handleKick(orgId: string, memberId: number) {
    updateWsState(orgId, (current) => ({
      busyMemberIds: [...current.busyMemberIds, memberId],
    }));

    try {
      await kickMember({ org_id: orgId, member_id: memberId });
      await loadMembers(orgId);
      await loadWorkspaces();
      showToast("Đã xóa thành viên", "Thành viên đã được gỡ khỏi workspace thành công.", "success");
    } catch {
      showToast("Không thể xóa thành viên", "Hãy thử lại sau hoặc kiểm tra quyền owner/admin hiện tại.", "error");
    } finally {
      updateWsState(orgId, (current) => ({
        busyMemberIds: current.busyMemberIds.filter((id) => id !== memberId),
      }));
    }
  }

  async function handleResendInvite(orgId: string, inviteId: string) {
    updateWsState(orgId, (current) => ({
      inviteActionState: { ...current.inviteActionState, [inviteId]: "resend" },
    }));

    try {
      await resendInvite({ org_id: orgId, invite_id: inviteId });
      await loadMembers(orgId);
      showToast("Đã gửi lại lời mời", "Lời mời đã được gửi lại cho thành viên và dashboard đã cập nhật.", "success");
    } catch {
      showToast("Gửi lại thất bại", "Không thể resend lời mời ở thời điểm này.", "error");
    } finally {
      updateWsState(orgId, (current) => {
        const next = { ...current.inviteActionState };
        delete next[inviteId];
        return { inviteActionState: next };
      });
    }
  }

  async function handleRevokeInvite(orgId: string, inviteId: string) {
    const previousInvites = wsStates[orgId]?.invites ?? [];

    updateWsState(orgId, (current) => ({
      invites: current.invites.filter((invite) => invite.invite_id !== inviteId),
      inviteActionState: { ...current.inviteActionState, [inviteId]: "revoke" },
    }));

    try {
      await cancelInvite({ org_id: orgId, invite_id: inviteId });
      showToast("Đã thu hồi lời mời", "Invite đã được revoke và dashboard đã cập nhật ngay lập tức.", "success");
    } catch {
      updateWsState(orgId, {
        invites: previousInvites,
      });
      showToast("Thu hồi thất bại", "Không thể revoke lời mời này. Hãy thử lại sau.", "error");
    } finally {
      updateWsState(orgId, (current) => {
        const next = { ...current.inviteActionState };
        delete next[inviteId];
        return { inviteActionState: next };
      });
      void loadWorkspaces();
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
      showToast("Không thể xóa workspace", `Workspace ${deletingWs.name} chưa thể xóa ở thời điểm này.`, "error");
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
                          busyMemberIds={state.busyMemberIds}
                          onKick={ws.can_manage_members ? (memberId) => handleKick(ws.org_id, memberId) : undefined}
                        />
                      </div>

                      <div className="workspace-side-column">
                        <div className="section-panel invite-section-panel">
                          <InvitePanel
                            orgId={ws.org_id}
                            onDone={() => loadMembers(ws.org_id)}
                          />
                        </div>

                        {(() => {
                          const pendingInvites = state.invites.filter((invite) => invite.status === "pending");

                          return pendingInvites.length > 0 ? (
                            <div className="section-panel invite-section-panel">
                              <InviteList
                                invites={pendingInvites}
                                busyInviteActions={state.inviteActionState}
                                onResend={ws.can_manage_members ? (inviteId) => handleResendInvite(ws.org_id, inviteId) : undefined}
                                onRevoke={ws.can_manage_members ? (inviteId) => handleRevokeInvite(ws.org_id, inviteId) : undefined}
                              />
                            </div>
                          ) : null;
                        })()}
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
              <button className="btn btn-ghost" onClick={() => setDeletingWs(null)} disabled={deleting}>
                Hủy
              </button>
              <button className="btn btn-danger" onClick={handleConfirmDelete} disabled={deleting}>
                {deleting ? "Đang xóa..." : "Xóa workspace"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="toast-stack" aria-live="polite" aria-atomic="true">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast-item toast-${toast.tone}`} role="status">
            <div className="toast-accent" aria-hidden="true">
              {toast.tone === "success" ? "✓" : toast.tone === "error" ? "!" : "i"}
            </div>
            <div className="toast-copy">
              <strong className="toast-title">{toast.title}</strong>
              <span className="toast-message">{toast.message}</span>
            </div>
            <button className="toast-close" onClick={() => setToasts((prev) => prev.filter((item) => item.id !== toast.id))}>
              ✕
            </button>
            <span className="toast-progress" aria-hidden="true" />
          </div>
        ))}
      </div>
    </main>
  );
}
