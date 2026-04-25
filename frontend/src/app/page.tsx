"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { DashboardSummary } from "@/components/dashboard-summary";
import { WorkspaceCard } from "@/components/workspace-card";
import { WorkspaceDetailPanel } from "@/components/workspace-detail-panel";
import { InvitePanel } from "@/components/invite-panel";
import { ImportDialog } from "@/components/import-dialog";
import { DashboardViewToggle, type DashboardViewMode } from "@/components/dashboard-view-toggle";
import { CompactWorkspaceCard } from "@/components/compact-workspace-card";
import { GlobalUnauthorizedAlert } from "@/components/global-unauthorized-alert";
import { RenameWorkspaceDialog } from "@/components/rename-workspace-dialog";
import { ToastStack } from "@/components/toast-stack";
import { UpdateTokenDialog } from "@/components/update-token-dialog";
import {
  getWorkspaces,
  getWorkspaceDetails,
  invalidateApiCache,
} from "@/lib/api";
import {
  formatDashboardDateLabel,
  formatDashboardSyncTime,
  getActionErrorCopy,
} from "@/lib/dashboard-formatters";
import { useWorkspaceTokenRefreshLifecycle } from "@/lib/use-workspace-token-refresh";
import { useDashboardToasts, type ToastTone } from "@/lib/use-dashboard-toasts";
import { useGlobalUnauthorizedFindings } from "@/lib/use-global-unauthorized-findings";
import { useWorkspaceEvents } from "@/lib/use-workspace-events";
import {
  applyWorkspaceSummaryList,
  compareWorkspaceExpiry,
  mergeInviteLists,
  mergeWorkspaceRecordList,
  upsertInvite,
} from "@/lib/workspace-state";
import { DEFAULT_WS_STATE, type WorkspaceState } from "@/lib/workspace-dashboard-state";
import { useWorkspaceLoadAndSync } from "@/lib/use-workspace-load-and-sync";
import { useWorkspaceMemberInviteActions } from "@/lib/use-workspace-member-invite-actions";
import { useWorkspaceDeleteAction } from "@/lib/use-workspace-delete-action";
import { useWorkspaceRenameAction } from "@/lib/use-workspace-rename-action";
import { useWorkspaceTokenActions } from "@/lib/use-workspace-token-actions";
import { useWorkspaceRealtimeHandlers } from "@/lib/use-workspace-realtime-handlers";
import type { Workspace } from "@/types/api";

const EVENT_REFRESH_WINDOW_MS = 450;

export default function DashboardPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [wsStates, setWsStates] = useState<Record<string, WorkspaceState>>({});
  const { toasts, showToast, dismissToast } = useDashboardToasts();
  const [loading, setLoading] = useState(true);
  const [showImport, setShowImport] = useState(false);
  const [viewMode, setViewMode] = useState<DashboardViewMode>("compact");
  const [focusedWorkspaceId, setFocusedWorkspaceId] = useState<string | null>(null);
  const [managedWorkspaceId, setManagedWorkspaceId] = useState<string | null>(null);
  const [renamingWorkspace, setRenamingWorkspace] = useState<Workspace | null>(null);
  const [renameSubmitting, setRenameSubmitting] = useState(false);
  const [renameError, setRenameError] = useState<string | null>(null);
  const [tokenWorkspace, setTokenWorkspace] = useState<Workspace | null>(null);
  const [tokenSubmitting, setTokenSubmitting] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [deletingWs, setDeletingWs] = useState<Workspace | null>(null);
  const [deleting, setDeleting] = useState(false);
  const {
    findings: globalUnauthorizedFindings,
    dismissed: unauthorizedBannerDismissed,
    refreshFindings: refreshGlobalUnauthorizedFindings,
    dismissFindings: dismissGlobalUnauthorizedFindings,
  } = useGlobalUnauthorizedFindings();

  const detailRefreshTimersRef = useRef(new Map<string, number>());
  const workspaceRefreshTimerRef = useRef<number | null>(null);
  const workspaceListRequestVersionRef = useRef(0);
  const workspaceDetailRequestVersionRef = useRef(new Map<string, number>());
  const wsStatesRef = useRef<Record<string, WorkspaceState>>({});
  const loadWorkspacesRef = useRef<
    ((options?: { silent?: boolean; forceFresh?: boolean }) => Promise<void>) | null
  >(null);
  const refreshWorkspaceDetailsRef = useRef<((orgId: string) => Promise<void>) | null>(null);
  const triggerPostActionRefreshRef = useRef<
    ((orgId?: string, options?: { immediate?: boolean; includeDetails?: boolean }) => Promise<void>) | null
  >(null);
  const showToastRef = useRef<
    ((title: string, message: string, tone?: ToastTone, dedupeKey?: string) => void) | null
  >(null);
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

  const loadWorkspaces = useCallback(async (options?: { silent?: boolean; forceFresh?: boolean }) => {
    const requestVersion = workspaceListRequestVersionRef.current + 1;
    workspaceListRequestVersionRef.current = requestVersion;

    try {
      if (!options?.silent) {
        setLoading(true);
      }
      const data = await getWorkspaces({ forceFresh: options?.forceFresh });
      if (workspaceListRequestVersionRef.current !== requestVersion) {
        return;
      }
      setWorkspaces(data);
    } catch (error) {
      if (workspaceListRequestVersionRef.current !== requestVersion) {
        return;
      }
      showToast(
        "Không thể tải workspace",
        getActionErrorCopy("sync", error),
        "error"
      );
    } finally {
      if (!options?.silent && workspaceListRequestVersionRef.current === requestVersion) {
        setLoading(false);
      }
    }
  }, []);

  const refreshWorkspaceDetails = useCallback(async (orgId: string) => {
    const requestVersion = (workspaceDetailRequestVersionRef.current.get(orgId) ?? 0) + 1;
    workspaceDetailRequestVersionRef.current.set(orgId, requestVersion);

    try {
      const details = await getWorkspaceDetails(orgId, { forceFresh: true });

      if (workspaceDetailRequestVersionRef.current.get(orgId) !== requestVersion) {
        return;
      }

      updateWsState(orgId, {
        members: details.members,
        loadedMembers: true,
        invites: mergeInviteLists(
          wsStatesRef.current[orgId]?.invites ?? [],
          details.invites,
        ),
        syncing: false,
      });
    } catch (error) {
      if (workspaceDetailRequestVersionRef.current.get(orgId) !== requestVersion) {
        return;
      }

      updateWsState(orgId, { syncing: false });
      showToast(
        "Không thể làm mới chi tiết workspace",
        `Workspace ${orgId}: ${getActionErrorCopy("sync", error)}`,
        "error"
      );
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

  const scheduleWorkspaceListRefresh = useCallback(
    (delayMs = EVENT_REFRESH_WINDOW_MS, options?: { forceFresh?: boolean }) => {
      if (workspaceRefreshTimerRef.current) {
        return;
      }

      workspaceRefreshTimerRef.current = window.setTimeout(() => {
        workspaceRefreshTimerRef.current = null;
        if (options?.forceFresh) {
          invalidateApiCache();
        }
        void loadWorkspacesRef.current?.({
          silent: true,
          forceFresh: options?.forceFresh,
        });
      }, delayMs);
    },
    []
  );

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

  const refreshWorkspaceListForTokenEvents = useCallback(
    (options?: { silent?: boolean; forceFresh?: boolean }) =>
      loadWorkspacesRef.current?.(options),
    []
  );

  const setWorkspaceSyncingForTokenEvents = useCallback(
    (orgId: string, syncing: boolean) => updateWsState(orgId, { syncing }),
    [updateWsState]
  );

  const { clearTokenRefreshPolling, handleTokenRefreshEvent, startTokenRefreshPolling, stopTokenRefreshPolling } = useWorkspaceTokenRefreshLifecycle({
    applyWorkspaceSummary,
    mergeWorkspaceRecord,
    refreshWorkspaceList: refreshWorkspaceListForTokenEvents,
    scheduleWorkspaceDetailRefresh,
    setWorkspaceSyncing: setWorkspaceSyncingForTokenEvents,
    setWorkspaces,
    showToast,
  });

  const triggerPostActionRefresh = useCallback(
    async (
      orgId?: string,
      options?: { immediate?: boolean; includeDetails?: boolean }
    ) => {
      const includeDetails = options?.includeDetails ?? true;

      if (options?.immediate) {
        await loadWorkspacesRef.current?.({ silent: true, forceFresh: true });
        if (orgId && includeDetails) {
          const state = wsStatesRef.current[orgId] ?? DEFAULT_WS_STATE;
          if (state.loadedMembers) {
            await refreshWorkspaceDetailsRef.current?.(orgId);
          }
        }
        return;
      }

      scheduleWorkspaceListRefresh(undefined, { forceFresh: true });
      if (orgId && includeDetails) {
        scheduleWorkspaceDetailRefresh(orgId);
      }
    },
    [scheduleWorkspaceDetailRefresh, scheduleWorkspaceListRefresh]
  );

  const { handleSync, loadMembers } = useWorkspaceLoadAndSync({
    applyWorkspaceSummary,
    showToast,
    triggerPostActionRefresh,
    updateWsState,
    wsStatesRef,
  });

  const { handleKick, handleResendInvite, handleRevokeInvite } = useWorkspaceMemberInviteActions({
    applyWorkspaceSummary,
    showToast,
    triggerPostActionRefresh,
    updateWsState,
    wsStatesRef,
  });

  const { handleConfirmDelete } = useWorkspaceDeleteAction({
    deletingWs,
    focusedWorkspaceId,
    setDeleting,
    setDeletingWs,
    setFocusedWorkspaceId,
    setWorkspaces,
    setWsStates,
    showToast,
    triggerPostActionRefresh,
  });

  const { handleRenameWorkspace } = useWorkspaceRenameAction({
    applyWorkspaceSummary,
    mergeWorkspaceRecord,
    renamingWorkspace,
    setRenameError,
    setRenameSubmitting,
    setRenamingWorkspace,
    showToast,
    triggerPostActionRefreshRef,
  });

  const { handleRefreshWorkspaceToken, handleUpdateWorkspaceToken } = useWorkspaceTokenActions({
    applyWorkspaceSummary,
    mergeWorkspaceRecord,
    setTokenError,
    setTokenSubmitting,
    setTokenWorkspace,
    showToast,
    startTokenRefreshPolling,
    stopTokenRefreshPolling,
    tokenWorkspace,
    triggerPostActionRefreshRef,
  });

  useEffect(() => {
    triggerPostActionRefreshRef.current = triggerPostActionRefresh;
  }, [triggerPostActionRefresh]);

  const { handleWorkspaceEvent, handleWorkspaceEventsReconnect, recoverDashboardState } = useWorkspaceRealtimeHandlers({
    focusedWorkspaceId,
    handleTokenRefreshEvent,
    managedWorkspaceId,
    refreshGlobalUnauthorizedFindings,
    refreshWorkspaceDetailsRef,
    loadWorkspacesRef,
    scheduleWorkspaceDetailRefresh,
    scheduleWorkspaceListRefresh,
    setWorkspaces,
    showToastRef,
    updateWsState,
    wsStatesRef,
  });

  useWorkspaceEvents({
    onEvent: handleWorkspaceEvent,
    onReconnect: handleWorkspaceEventsReconnect,
  });

  useEffect(() => {
    void loadWorkspaces();
    void refreshGlobalUnauthorizedFindings();
  }, [loadWorkspaces, refreshGlobalUnauthorizedFindings]);

  useEffect(() => {
    return () => {
      if (workspaceRefreshTimerRef.current) {
        window.clearTimeout(workspaceRefreshTimerRef.current);
      }
      for (const timerId of detailRefreshTimersRef.current.values()) {
        window.clearTimeout(timerId);
      }
      detailRefreshTimersRef.current.clear();
      clearTokenRefreshPolling();
    };
  }, [clearTokenRefreshPolling]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void recoverDashboardState();
      }
    };

    const handleWindowFocus = () => {
      void recoverDashboardState();
    };

    const handleOnline = () => {
      void recoverDashboardState();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", handleWindowFocus);
    window.addEventListener("online", handleOnline);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", handleWindowFocus);
      window.removeEventListener("online", handleOnline);
    };
  }, [recoverDashboardState]);

  useEffect(() => {
    const workspaceIds = new Set(workspaces.map((workspace) => workspace.org_id));

    setWsStates((prev) => {
      const entries = Object.entries(prev).filter(([orgId]) => workspaceIds.has(orgId));
      if (entries.length === Object.keys(prev).length) {
        return prev;
      }
      return Object.fromEntries(entries);
    });

    for (const orgId of workspaceDetailRequestVersionRef.current.keys()) {
      if (!workspaceIds.has(orgId)) {
        workspaceDetailRequestVersionRef.current.delete(orgId);
      }
    }

    setFocusedWorkspaceId((current) =>
      current && !workspaceIds.has(current) ? null : current
    );
    setManagedWorkspaceId((current) =>
      current && !workspaceIds.has(current) ? null : current
    );
    setRenamingWorkspace((current) =>
      current && !workspaceIds.has(current.org_id) ? null : current
    );
    setTokenWorkspace((current) =>
      current && !workspaceIds.has(current.org_id) ? null : current
    );
    setDeletingWs((current) =>
      current && !workspaceIds.has(current.org_id) ? null : current
    );
  }, [workspaces]);

  function handleOpenRename(workspace: Workspace) {
    setRenameError(null);
    setRenamingWorkspace(workspace);
  }

  function handleOpenTokenUpdate(workspace: Workspace) {
    setTokenError(null);
    setTokenWorkspace(workspace);
  }

  async function handleManageWorkspace(workspace: Workspace) {
    setManagedWorkspaceId(workspace.org_id);
    setFocusedWorkspaceId(workspace.org_id);

    const state = wsStatesRef.current[workspace.org_id] ?? DEFAULT_WS_STATE;
    if (
      !state.loadedMembers &&
      (Boolean(workspace.last_sync) || workspace.member_count > 0)
    ) {
      await loadMembers(workspace.org_id);
    }
  }

  const totalMembers = workspaces.reduce((sum, workspace) => sum + (workspace.member_count ?? 0), 0);
  const totalPending = workspaces.reduce(
    (sum, workspace) => sum + (workspace.pending_invites ?? 0),
    0
  );
  const totalCapacity = workspaces.reduce((sum, workspace) => sum + (workspace.member_limit ?? 0), 0);
  const availableSlots = Math.max(totalCapacity - totalMembers, 0);
  // const syncErrors = workspaces.filter((workspace) => workspace.status === "error").length;
  const sortedWorkspaces = useMemo(
    () => [...workspaces].sort(compareWorkspaceExpiry),
    [workspaces]
  );
  const managedWorkspace = managedWorkspaceId
    ? sortedWorkspaces.find((workspace) => workspace.org_id === managedWorkspaceId) ?? null
    : null;
  const managedWorkspaceState = managedWorkspace
    ? wsStates[managedWorkspace.org_id] ?? DEFAULT_WS_STATE
    : DEFAULT_WS_STATE;

  return (
    <main className={`dashboard-layout${viewMode === "compact" ? " dashboard-layout-compact" : ""}`}>
      <div className="dashboard-header">
        <div className="dashboard-header-copy">
          <span className="eyebrow">Workspace control center</span>
          <h1 className="dashboard-title">ChatGPT Team Manager</h1>
          <p className="dashboard-subtitle">
            Theo dõi workspace, quản lý thành viên và xử lý lời mời trong một dashboard.
          </p>
        </div>
        <div className="dashboard-header-actions">
          <DashboardViewToggle value={viewMode} onChange={setViewMode} />
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

      {globalUnauthorizedFindings.length > 0 && !unauthorizedBannerDismissed && (
        <GlobalUnauthorizedAlert
          findings={globalUnauthorizedFindings}
          onDismiss={dismissGlobalUnauthorizedFindings}
        />
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

      {viewMode === "compact" ? (
        <section className="compact-teams-section" aria-labelledby="compact-teams-heading">
          <div className="compact-teams-section-header">
            <div className="compact-teams-heading-block">
              <span id="compact-teams-heading" className="compact-teams-kicker">Workspace collection</span>
            </div>
            <div className="compact-teams-divider" aria-hidden="true" />
          </div>

          <div className="compact-workspace-grid">
            {sortedWorkspaces.map((ws) => {
              const state = wsStates[ws.org_id] ?? DEFAULT_WS_STATE;
              const wsStatus =
                ws.status === "live"
                  ? "synced"
                  : ws.status === "error"
                    ? "error"
                    : "warning";

              return (
                <CompactWorkspaceCard
                  key={ws.org_id}
                  orgId={ws.org_id}
                  title={ws.name}
                  members={ws.member_count}
                  memberLimit={ws.member_limit}
                  pendingInvites={ws.pending_invites ?? 0}
                  expiresAt={ws.expires_at}
                  accessTokenExpiresAt={ws.access_token_expires_at}
                  lastSync={ws.last_sync}
                  syncing={state.syncing || ws.status === "syncing"}
                  status={wsStatus}
                  onRename={() => handleOpenRename(ws)}
                  onUpdateToken={() => void handleRefreshWorkspaceToken(ws)}
                  onSync={() => handleSync(ws.org_id)}
                  onDelete={() => setDeletingWs(ws)}
                  onManage={() => void handleManageWorkspace(ws)}
                />
              );
            })}
          </div>
        </section>
      ) : (
        <div className="workspace-list">
          {sortedWorkspaces.map((ws) => {
            const state = wsStates[ws.org_id] ?? DEFAULT_WS_STATE;
            const wsStatus =
              ws.status === "error"
                ? "error"
                : ws.pending_invites && ws.pending_invites > 0
                  ? "warning"
                  : "synced";

            return (
              <WorkspaceCard
                key={`${ws.org_id}-${focusedWorkspaceId === ws.org_id ? "focused" : "default"}`}
                orgId={ws.org_id}
                title={ws.name}
                members={ws.member_count}
                memberLimit={ws.member_limit}
                status={wsStatus}
                selected={focusedWorkspaceId === ws.org_id}
                lastSync={ws.last_sync}
                expiresAt={ws.expires_at}
                accessTokenExpiresAt={ws.access_token_expires_at}
                syncing={state.syncing || ws.status === "syncing"}
                isHot={Boolean(ws.is_hot)}
                syncReason={ws.sync_reason}
                onRename={() => handleOpenRename(ws)}
                onUpdateToken={() => void handleRefreshWorkspaceToken(ws)}
                onSync={() => handleSync(ws.org_id)}
                onDelete={() => setDeletingWs(ws)}
                onExpandedChange={(expanded) => {
                  if (expanded) {
                    setFocusedWorkspaceId(ws.org_id);
                  } else if (focusedWorkspaceId === ws.org_id) {
                    setFocusedWorkspaceId(null);
                  }

                  if (
                    expanded &&
                    !state.loadedMembers &&
                    (
                      Boolean(ws.last_sync) ||
                      ws.member_count > 0 ||
                      (ws.pending_invites ?? 0) > 0
                    )
                  ) {
                    void loadMembers(ws.org_id);
                  }
                }}
                expandedContent={
                  <WorkspaceDetailPanel
                    workspace={ws}
                    loadedMembers={state.loadedMembers}
                    syncing={state.syncing}
                    members={state.members}
                    invites={state.invites}
                    busyMemberIds={state.busyMemberIds}
                    inviteActionState={state.inviteActionState}
                    includePendingInvitesInLoadGate
                    onSync={() => handleSync(ws.org_id)}
                    onKick={
                      ws.can_manage_members
                        ? (memberId) => handleKick(ws.org_id, memberId)
                        : undefined
                    }
                    onResend={
                      ws.can_manage_members
                        ? (inviteId, email) => handleResendInvite(ws.org_id, inviteId, email)
                        : undefined
                    }
                    onRevoke={
                      ws.can_manage_members
                        ? (inviteId) => handleRevokeInvite(ws.org_id, inviteId)
                        : undefined
                    }
                    invitePanel={
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
                    }
                  />
                }
              />
            );
          })}
        </div>
      )}

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
            void loadWorkspacesRef.current?.({ silent: true, forceFresh: true });

            if (targetOrgId) {
              void triggerPostActionRefreshRef.current?.(targetOrgId, {
                includeDetails: refreshHint?.include_details ?? true,
              });
            }
          }}
        />
      )}

      {managedWorkspace && (
        <div className="dialog-overlay workspace-focus-overlay" onClick={() => setManagedWorkspaceId(null)}>
          <div className="workspace-focus-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="workspace-focus-header">
              <div className="workspace-focus-copy">
                <span className="workspace-focus-eyebrow">Manage Team</span>
                <h2>{managedWorkspace.name}</h2>
                <p className="workspace-focus-subtitle">
                  <span>{managedWorkspace.member_count} members</span>
                  <span className="meta-dot">•</span>
                  <span>{formatDashboardDateLabel("Plan", managedWorkspace.expires_at)}</span>
                  <span className="meta-dot">•</span>
                  <span>Last sync {formatDashboardSyncTime(managedWorkspace.last_sync)}</span>
                </p>
              </div>
              <button
                type="button"
                className="compact-toolbar-icon workspace-focus-close"
                onClick={() => setManagedWorkspaceId(null)}
                aria-label={`Đóng workspace ${managedWorkspace.name}`}
              >
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                  <path d="M5 5l10 10" />
                  <path d="M15 5 5 15" />
                </svg>
              </button>
            </div>

            <div className="workspace-focus-body workspace-detail">
              <WorkspaceDetailPanel
                workspace={managedWorkspace}
                loadedMembers={managedWorkspaceState.loadedMembers}
                syncing={managedWorkspaceState.syncing}
                members={managedWorkspaceState.members}
                invites={managedWorkspaceState.invites}
                busyMemberIds={managedWorkspaceState.busyMemberIds}
                inviteActionState={managedWorkspaceState.inviteActionState}
                onSync={() => handleSync(managedWorkspace.org_id)}
                onKick={
                  managedWorkspace.can_manage_members
                    ? (memberId) => handleKick(managedWorkspace.org_id, memberId)
                    : undefined
                }
                onResend={
                  managedWorkspace.can_manage_members
                    ? (inviteId, email) => handleResendInvite(managedWorkspace.org_id, inviteId, email)
                    : undefined
                }
                onRevoke={
                  managedWorkspace.can_manage_members
                    ? (inviteId) => handleRevokeInvite(managedWorkspace.org_id, inviteId)
                    : undefined
                }
                invitePanel={
                  <InvitePanel
                    orgId={managedWorkspace.org_id}
                    onDone={({ invite, result }) => {
                      if (invite) {
                        updateWsState(managedWorkspace.org_id, (current) => ({
                          invites: upsertInvite(current.invites, invite),
                          loadedMembers: true,
                        }));
                      }

                      applyWorkspaceSummary(result.updated_summary);

                      void triggerPostActionRefreshRef.current?.(managedWorkspace.org_id, {
                        includeDetails: result.refresh_hint?.include_details ?? !invite,
                      });
                    }}
                  />
                }
              />
            </div>
          </div>
        </div>
      )}

      {renamingWorkspace && (
        <RenameWorkspaceDialog
          workspaceName={renamingWorkspace.name}
          workspaceOrgId={renamingWorkspace.org_id}
          submitting={renameSubmitting}
          error={renameError}
          onClose={() => {
            if (!renameSubmitting) {
              setRenameError(null);
              setRenamingWorkspace(null);
            }
          }}
          onSubmit={handleRenameWorkspace}
        />
      )}

      {tokenWorkspace && (
        <UpdateTokenDialog
          workspaceName={tokenWorkspace.name}
          workspaceOrgId={tokenWorkspace.org_id}
          submitting={tokenSubmitting}
          error={tokenError}
          onClose={() => {
            if (!tokenSubmitting) {
              setTokenError(null);
              setTokenWorkspace(null);
            }
          }}
          onSubmit={handleUpdateWorkspaceToken}
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

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </main>
  );
}
