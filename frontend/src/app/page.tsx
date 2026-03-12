"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { DashboardSummary } from "@/components/dashboard-summary";
import { WorkspaceCard } from "@/components/workspace-card";
import { MemberTable } from "@/components/member-table";
import { InvitePanel } from "@/components/invite-panel";
import { InviteList } from "@/components/invite-list";
import { ImportDialog } from "@/components/import-dialog";
import {
  buildWorkspaceEventsUrl,
  getWorkspaces,
  getWorkspaceMembers,
  invalidateApiCache,
  kickMember,
  listInvites,
  parseWorkspaceEvent,
  syncWorkspace,
  deleteWorkspace,
  resendInvite,
  cancelInvite,
} from "@/lib/api";
import {
  applyWorkspaceSummaryList,
  compareWorkspaceExpiry,
  mergeWorkspaceRecordList,
  removeInvite,
  removeMember,
  replaceInvite,
  upsertInvite,
} from "@/lib/workspace-state";
import type { Workspace, Member, Invite, WorkspaceEvent } from "@/types/api";

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
  dedupeKey?: string;
};

const DEFAULT_WS_STATE: WorkspaceState = {
  members: [],
  invites: [],
  loadedMembers: false,
  syncing: false,
  busyMemberIds: [],
  inviteActionState: {},
};

const EVENT_REFRESH_WINDOW_MS = 450;

export default function DashboardPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [wsStates, setWsStates] = useState<Record<string, WorkspaceState>>({});
  const [toasts, setToasts] = useState<ToastState[]>([]);
  const [loading, setLoading] = useState(true);
  const [showImport, setShowImport] = useState(false);
  const [deletingWs, setDeletingWs] = useState<Workspace | null>(null);
  const [deleting, setDeleting] = useState(false);

  const inflightMemberLoads = useRef(new Map<string, Promise<void>>());
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const seenEventSequencesRef = useRef(new Set<number>());
  const detailRefreshTimersRef = useRef(new Map<string, number>());
  const workspaceRefreshTimerRef = useRef<number | null>(null);
  const wsStatesRef = useRef<Record<string, WorkspaceState>>({});
  const loadWorkspacesRef = useRef<((options?: { silent?: boolean }) => Promise<void>) | null>(null);
  const refreshWorkspaceDetailsRef = useRef<((orgId: string) => Promise<void>) | null>(null);
  const triggerPostActionRefreshRef = useRef<
    ((orgId?: string, options?: { immediate?: boolean; includeDetails?: boolean }) => Promise<void>) | null
  >(null);
  const showToastRef = useRef<((title: string, message: string, tone?: ToastState["tone"], dedupeKey?: string) => void) | null>(null);

  function showToast(
    title: string,
    message: string,
    tone: ToastState["tone"] = "info",
    dedupeKey?: string
  ) {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => {
      if (dedupeKey) {
        const alreadyShown = prev.some((toast) => toast.dedupeKey === dedupeKey);
        if (alreadyShown) {
          return prev;
        }
      }
      return [...prev, { id, title, message, tone, dedupeKey }];
    });
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 3600);
  }

  const updateWsState = useCallback(
    (
      orgId: string,
      patch:
        | Partial<WorkspaceState>
        | ((current: WorkspaceState) => Partial<WorkspaceState>)
    ) => {
      setWsStates((prev) => {
        const current = prev[orgId] ?? DEFAULT_WS_STATE;
        const nextPatch = typeof patch === "function" ? patch(current) : patch;

        return {
          ...prev,
          [orgId]: { ...current, ...nextPatch },
        };
      });
    },
    []
  );

  const applyWorkspaceSummary = useCallback((summary?: Partial<Workspace> | null) => {
    setWorkspaces((prev) => applyWorkspaceSummaryList(prev, summary));
  }, []);

  const mergeWorkspaceRecord = useCallback((record?: Workspace | null) => {
    setWorkspaces((prev) => mergeWorkspaceRecordList(prev, record));
  }, []);

  const loadWorkspaces = useCallback(async (options?: { silent?: boolean }) => {
    try {
      if (!options?.silent) {
        setLoading(true);
      }
      const data = await getWorkspaces();
      setWorkspaces(data);
    } catch {
      showToast(
        "Không thể tải workspace",
        "Hãy kiểm tra backend đang chạy và thử tải lại dashboard.",
        "error"
      );
    } finally {
      if (!options?.silent) {
        setLoading(false);
      }
    }
  }, []);

  const refreshWorkspaceDetails = useCallback(async (orgId: string) => {
    try {
      const [members, invites] = await Promise.all([
        getWorkspaceMembers(orgId),
        listInvites(orgId).catch(() => [] as Invite[]),
      ]);
      updateWsState(orgId, {
        members,
        invites,
        loadedMembers: true,
        syncing: false,
      });
    } catch {
      updateWsState(orgId, { syncing: false });
    }
  }, [updateWsState]);

  useEffect(() => {
    wsStatesRef.current = wsStates;
  }, [wsStates]);

  useEffect(() => {
    loadWorkspacesRef.current = loadWorkspaces;
  }, [loadWorkspaces]);

  useEffect(() => {
    refreshWorkspaceDetailsRef.current = refreshWorkspaceDetails;
  }, [refreshWorkspaceDetails]);

  useEffect(() => {
    showToastRef.current = showToast;
  }, [showToast]);

  const scheduleWorkspaceListRefresh = useCallback((delayMs = EVENT_REFRESH_WINDOW_MS) => {
    if (workspaceRefreshTimerRef.current) {
      return;
    }

    workspaceRefreshTimerRef.current = window.setTimeout(() => {
      workspaceRefreshTimerRef.current = null;
      void loadWorkspacesRef.current?.({ silent: true });
    }, delayMs);
  }, []);

  const scheduleWorkspaceDetailRefresh = useCallback((orgId: string) => {
    const state = wsStatesRef.current[orgId] ?? DEFAULT_WS_STATE;
    if (!state.loadedMembers) {
      return;
    }

    const existingTimer = detailRefreshTimersRef.current.get(orgId);
    if (existingTimer) {
      return;
    }

    const timerId = window.setTimeout(() => {
      detailRefreshTimersRef.current.delete(orgId);
      void refreshWorkspaceDetailsRef.current?.(orgId);
    }, EVENT_REFRESH_WINDOW_MS);

    detailRefreshTimersRef.current.set(orgId, timerId);
  }, []);

  const triggerPostActionRefresh = useCallback(
    async (
      orgId?: string,
      options?: { immediate?: boolean; includeDetails?: boolean }
    ) => {
      const includeDetails = options?.includeDetails ?? true;

      if (options?.immediate) {
        await loadWorkspacesRef.current?.({ silent: true });
        if (orgId && includeDetails) {
          const state = wsStatesRef.current[orgId] ?? DEFAULT_WS_STATE;
          if (state.loadedMembers) {
            await refreshWorkspaceDetailsRef.current?.(orgId);
          }
        }
        return;
      }

      scheduleWorkspaceListRefresh();
      if (orgId && includeDetails) {
        scheduleWorkspaceDetailRefresh(orgId);
      }
    },
    [scheduleWorkspaceDetailRefresh, scheduleWorkspaceListRefresh]
  );

  useEffect(() => {
    triggerPostActionRefreshRef.current = triggerPostActionRefresh;
  }, [triggerPostActionRefresh]);

  const handleWorkspaceEvent = useCallback((event: WorkspaceEvent) => {
    if (seenEventSequencesRef.current.has(event.sequence)) {
      return;
    }
    seenEventSequencesRef.current.add(event.sequence);
    if (seenEventSequencesRef.current.size > 100) {
      const recentSequences = Array.from(seenEventSequencesRef.current).slice(-50);
      seenEventSequencesRef.current = new Set(recentSequences);
    }

    if (event.type === "heartbeat") {
      return;
    }

    if (!event.org_id) {
      return;
    }

    if (event.type === "workspace_scheduled") {
      setWorkspaces((prev) =>
        prev.map((workspace) =>
          workspace.org_id === event.org_id
            ? {
                ...workspace,
                sync_reason: event.reason ?? workspace.sync_reason,
                next_sync_at:
                  event.next_sync_at !== undefined ? event.next_sync_at : workspace.next_sync_at,
                hot_until: event.hot_until !== undefined ? event.hot_until : workspace.hot_until,
                is_hot: event.is_hot ?? workspace.is_hot,
                sync_priority: event.priority ?? workspace.sync_priority,
              }
            : workspace
        )
      );
      return;
    }

    if (event.type === "sync_started") {
      updateWsState(event.org_id, { syncing: true });
      scheduleWorkspaceListRefresh();
      return;
    }

    if (event.type === "workspace_updated") {
      updateWsState(event.org_id, { syncing: false });
      scheduleWorkspaceListRefresh();
      scheduleWorkspaceDetailRefresh(event.org_id);
      setWorkspaces((prev) =>
        prev.map((workspace) =>
          workspace.org_id === event.org_id
            ? {
                ...workspace,
                sync_reason: event.reason ?? workspace.sync_reason,
                next_sync_at:
                  event.next_sync_at !== undefined ? event.next_sync_at : workspace.next_sync_at,
                hot_until: event.hot_until !== undefined ? event.hot_until : workspace.hot_until,
                is_hot: event.is_hot ?? workspace.is_hot,
                pending_invites:
                  event.summary?.pending_invites ?? workspace.pending_invites,
                member_count: event.summary?.member_count ?? workspace.member_count,
                last_sync: event.summary?.last_sync ?? workspace.last_sync,
                status: event.summary?.status ?? workspace.status,
              }
            : workspace
        )
      );
      if (event.trigger !== "auto") {
        showToastRef.current?.(
          "Realtime sync hoàn tất",
          `Workspace ${event.org_id} đã được cập nhật tự động.`,
          "success",
          `workspace-updated-${event.org_id}-${event.trigger ?? "manual"}`
        );
      }
      return;
    }

    if (event.type === "sync_failed") {
      updateWsState(event.org_id, { syncing: false });
      scheduleWorkspaceListRefresh();
      showToastRef.current?.(
        "Realtime sync lỗi",
        event.error?.message
          ? `Workspace ${event.org_id}: ${event.error.message}`
          : `Workspace ${event.org_id} đồng bộ thất bại.`,
        "error",
        `sync-failed-${event.org_id}`
      );
    }
  }, [scheduleWorkspaceDetailRefresh, scheduleWorkspaceListRefresh, updateWsState]);

  const connectWorkspaceEvents = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(buildWorkspaceEventsUrl());
    eventSourceRef.current = eventSource;

    const onMessage = (message: MessageEvent<string>) => {
      try {
        const payload = parseWorkspaceEvent(message.data);
        reconnectAttemptsRef.current = 0;
        handleWorkspaceEvent(payload);
      } catch {
        // ignore malformed events
      }
    };

    const onError = () => {
      eventSource.close();
      eventSourceRef.current = null;

      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }

      const attempt = Math.min(reconnectAttemptsRef.current + 1, 5);
      reconnectAttemptsRef.current = attempt;
      const delay = Math.min(1000 * 2 ** (attempt - 1), 15000);

      reconnectTimerRef.current = window.setTimeout(() => {
        connectWorkspaceEvents();
        void loadWorkspacesRef.current?.({ silent: true });
      }, delay);
    };

    eventSource.onmessage = onMessage;
    eventSource.addEventListener("heartbeat", onMessage as EventListener);
    eventSource.addEventListener("workspace_scheduled", onMessage as EventListener);
    eventSource.addEventListener("sync_started", onMessage as EventListener);
    eventSource.addEventListener("workspace_updated", onMessage as EventListener);
    eventSource.addEventListener("sync_failed", onMessage as EventListener);
    eventSource.onerror = onError;
  }, [handleWorkspaceEvent]);

  useEffect(() => {
    void loadWorkspaces();
  }, [loadWorkspaces]);

  useEffect(() => {
    connectWorkspaceEvents();

    return () => {
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }
      if (workspaceRefreshTimerRef.current) {
        window.clearTimeout(workspaceRefreshTimerRef.current);
      }
      for (const timerId of detailRefreshTimersRef.current.values()) {
        window.clearTimeout(timerId);
      }
      detailRefreshTimersRef.current.clear();
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connectWorkspaceEvents]);

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
        showToast(
          "Không thể tải dữ liệu workspace",
          `Workspace ${orgId} hiện chưa đọc được members hoặc invites.`,
          "error"
        );
      } finally {
        updateWsState(orgId, { syncing: false });
        inflightMemberLoads.current.delete(orgId);
      }
    })();

    inflightMemberLoads.current.set(orgId, request);
    return request;
  }

  async function handleSync(orgId: string) {
    updateWsState(orgId, { syncing: true });
    try {
      await syncWorkspace(orgId);
      const state = wsStatesRef.current[orgId] ?? DEFAULT_WS_STATE;

      if (state.loadedMembers) {
        void triggerPostActionRefresh(orgId, { includeDetails: true });
      } else {
        await loadMembers(orgId);
      }

      showToast(
        "Đồng bộ hoàn tất",
        `Workspace ${orgId} đã được cập nhật dữ liệu mới nhất.`,
        "success"
      );
    } catch {
      showToast(
        "Sync thất bại",
        `Workspace ${orgId} chưa thể đồng bộ. Token có thể đã hết hạn.`,
        "error"
      );
      updateWsState(orgId, { syncing: false });
    }
  }

  async function handleKick(orgId: string, memberId: number) {
    updateWsState(orgId, (current) => ({
      busyMemberIds: [...current.busyMemberIds, memberId],
    }));

    try {
      const result = await kickMember({ org_id: orgId, member_id: memberId });
      const removedMemberId = result.member_id ?? memberId;
      updateWsState(orgId, (current) => ({
        members: removeMember(current.members, removedMemberId),
      }));
      applyWorkspaceSummary(result.updated_summary);
      void triggerPostActionRefresh(orgId, {
        includeDetails: result.refresh_hint?.include_details ?? true,
      });
      showToast(
        "Đã xóa thành viên",
        "Thành viên đã được gỡ khỏi workspace thành công.",
        "success"
      );
    } catch {
      showToast(
        "Không thể xóa thành viên",
        "Hãy thử lại sau hoặc kiểm tra quyền owner/admin hiện tại.",
        "error"
      );
    } finally {
      updateWsState(orgId, (current) => ({
        busyMemberIds: current.busyMemberIds.filter((id) => id !== memberId),
      }));
    }
  }

  async function handleResendInvite(orgId: string, inviteId: string) {
    updateWsState(orgId, (current) => ({
      inviteActionState: {
        ...current.inviteActionState,
        [inviteId]: "resend",
      },
    }));

    try {
      const result = await resendInvite({ org_id: orgId, invite_id: inviteId });
      if (result.updated_record) {
        const updatedInvite = result.updated_record;
        updateWsState(orgId, (current) => ({
          invites: replaceInvite(current.invites, inviteId, updatedInvite),
        }));
      }
      applyWorkspaceSummary(result.updated_summary);
      void triggerPostActionRefresh(orgId, {
        includeDetails: result.refresh_hint?.include_details ?? true,
      });
      showToast(
        "Đã gửi lại lời mời",
        "Lời mời đã được gửi lại cho thành viên và dashboard đã cập nhật.",
        "success"
      );
    } catch {
      showToast(
        "Gửi lại thất bại",
        "Không thể resend lời mời ở thời điểm này.",
        "error"
      );
    } finally {
      updateWsState(orgId, (current) => {
        const next = { ...current.inviteActionState };
        delete next[inviteId];
        return { inviteActionState: next };
      });
    }
  }

  async function handleRevokeInvite(orgId: string, inviteId: string) {
    const previousInvites = wsStatesRef.current[orgId]?.invites ?? [];

    updateWsState(orgId, (current) => ({
      invites: removeInvite(current.invites, inviteId),
      inviteActionState: {
        ...current.inviteActionState,
        [inviteId]: "revoke",
      },
    }));

    try {
      const result = await cancelInvite({ org_id: orgId, invite_id: inviteId });
      applyWorkspaceSummary(result.updated_summary);
      void triggerPostActionRefresh(orgId, {
        includeDetails: result.refresh_hint?.include_details ?? true,
      });
      showToast(
        "Đã thu hồi lời mời",
        "Invite đã được revoke và dashboard đã cập nhật ngay lập tức.",
        "success"
      );
    } catch {
      updateWsState(orgId, {
        invites: previousInvites,
      });
      showToast(
        "Thu hồi thất bại",
        "Không thể revoke lời mời này. Hãy thử lại sau.",
        "error"
      );
    } finally {
      updateWsState(orgId, (current) => {
        const next = { ...current.inviteActionState };
        delete next[inviteId];
        return { inviteActionState: next };
      });
    }
  }

  async function handleConfirmDelete() {
    if (!deletingWs) return;
    setDeleting(true);
    try {
      const result = await deleteWorkspace(deletingWs.org_id);
      setWorkspaces((prev) =>
        prev.filter((workspace) => workspace.org_id !== (result.deleted_org_id ?? deletingWs.org_id))
      );
      setWsStates((prev) => {
        const next = { ...prev };
        delete next[deletingWs.org_id];
        return next;
      });
      void triggerPostActionRefresh(undefined, {
        includeDetails: result.refresh_hint?.include_details ?? false,
      });
      setDeletingWs(null);
    } catch {
      showToast(
        "Không thể xóa workspace",
        `Workspace ${deletingWs.name} chưa thể xóa ở thời điểm này.`,
        "error"
      );
    } finally {
      setDeleting(false);
    }
  }

  const totalMembers = workspaces.reduce((sum, workspace) => sum + (workspace.member_count ?? 0), 0);
  const totalPending = workspaces.reduce(
    (sum, workspace) => sum + (workspace.pending_invites ?? 0),
    0
  );
  const totalCapacity = workspaces.length * 7;
  const availableSlots = Math.max(totalCapacity - totalMembers, 0);
  // const syncErrors = workspaces.filter((workspace) => workspace.status === "error").length;
  const sortedWorkspaces = useMemo(
    () => [...workspaces].sort(compareWorkspaceExpiry),
    [workspaces]
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

      {/* syncErrors is intentionally commented out while the Health card is hidden.
          syncErrors={syncErrors} */}
      <DashboardSummary
        totalTeams={workspaces.length}
        totalMembers={totalMembers}
        availableSlots={availableSlots}
        pendingInvites={totalPending}
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

      <div className="workspace-list">
        {sortedWorkspaces.map((ws) => {
          const state = wsStates[ws.org_id] ?? DEFAULT_WS_STATE;
          const wsStatus =
            ws.status === "live"
              ? "synced"
              : ws.status === "error"
                ? "error"
                : "warning";

          return (
            <WorkspaceCard
              key={ws.org_id}
              title={ws.name}
              members={ws.member_count}
              memberLimit={ws.member_limit}
              status={wsStatus}
              lastSync={ws.last_sync}
              expiresAt={ws.expires_at}
              syncing={state.syncing || ws.status === "syncing"}
              isHot={Boolean(ws.is_hot)}
              syncReason={ws.sync_reason}
              onSync={() => handleSync(ws.org_id)}
              onDelete={() => setDeletingWs(ws)}
              onExpandedChange={(expanded) => {
                if (
                  expanded &&
                  !state.loadedMembers &&
                  (Boolean(ws.last_sync) || ws.member_count > 0)
                ) {
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
                            {state.syncing
                              ? "Workspace đang đồng bộ dữ liệu"
                              : ws.last_sync || ws.member_count > 0
                                ? "Đang tải chi tiết workspace"
                                : "Workspace data chưa được tải"}
                          </h3>
                          <p className="section-description">
                            {state.syncing
                              ? "Hệ thống đang sync workspace rồi tải members và invites mới nhất."
                              : ws.last_sync || ws.member_count > 0
                                ? "Đang đọc dữ liệu members và invites đã sync trước đó để hiển thị chi tiết workspace."
                                : "Đồng bộ ngay để lấy danh sách thành viên và lời mời mới nhất từ ChatGPT."}
                          </p>
                          {ws.sync_error && (
                            <p
                              className="section-description"
                              style={{ color: "#ff8f8f" }}
                            >
                              Lỗi gần nhất: {ws.sync_error}
                            </p>
                          )}
                        </div>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          gap: "12px",
                          alignItems: "center",
                          flexWrap: "wrap",
                        }}
                      >
                        {ws.last_sync || ws.member_count > 0 || state.syncing ? (
                          <>
                            <div className="loading-spinner" />
                            <span className="workspace-helper-copy">
                              {state.syncing
                                ? "Đang đồng bộ và tải chi tiết workspace..."
                                : "Đang tải dữ liệu chi tiết của workspace..."}
                            </span>
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
                            <span className="workspace-helper-copy">
                              Workspace này chưa có dữ liệu cục bộ, hãy sync lần đầu để tải members và invites.
                            </span>
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
                          onKick={
                            ws.can_manage_members
                              ? (memberId) => handleKick(ws.org_id, memberId)
                              : undefined
                          }
                        />
                      </div>

                      <div className="workspace-side-column">
                        <div className="section-panel invite-section-panel">
                          <InvitePanel
                            orgId={ws.org_id}
                            onDone={({ invite, result }) => {
                              if (invite) {
                                updateWsState(ws.org_id, (current) => ({
                                  invites: upsertInvite(current.invites, invite),
                                  loadedMembers: true,
                                }));
                              }

                              applyWorkspaceSummary(result.updated_summary);

                              void triggerPostActionRefreshRef.current?.(ws.org_id, {
                                includeDetails: result.refresh_hint?.include_details ?? !invite,
                              });
                            }}
                          />
                        </div>

                        {(() => {
                          const pendingInvites = state.invites.filter(
                            (invite) => invite.status === "pending"
                          );

                          return pendingInvites.length > 0 ? (
                            <div className="section-panel invite-section-panel">
                              <InviteList
                                invites={pendingInvites}
                                busyInviteActions={state.inviteActionState}
                                onResend={
                                  ws.can_manage_members
                                    ? (inviteId) => handleResendInvite(ws.org_id, inviteId)
                                    : undefined
                                }
                                onRevoke={
                                  ws.can_manage_members
                                    ? (inviteId) => handleRevokeInvite(ws.org_id, inviteId)
                                    : undefined
                                }
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
          onImported={({ importedOrgId, updatedRecords, refreshHint }) => {
            setShowImport(false);

            updatedRecords.forEach((record) => {
              mergeWorkspaceRecord(record);
            });

            const targetOrgId = importedOrgId ?? updatedRecords[0]?.org_id;
            if (targetOrgId) {
              updateWsState(targetOrgId, { syncing: true });
            }

            invalidateApiCache();
            void loadWorkspacesRef.current?.({ silent: true });

            if (targetOrgId) {
              void triggerPostActionRefreshRef.current?.(targetOrgId, {
                includeDetails: refreshHint?.include_details ?? true,
              });
            }
          }}
        />
      )}

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
            <button
              className="toast-close"
              onClick={() =>
                setToasts((prev) => prev.filter((item) => item.id !== toast.id))
              }
            >
              ✕
            </button>
            <span className="toast-progress" aria-hidden="true" />
          </div>
        ))}
      </div>
    </main>
  );
}
