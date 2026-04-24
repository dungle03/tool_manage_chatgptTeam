import type { ReactNode } from "react";

import { InviteList } from "@/components/invite-list";
import { MemberTable } from "@/components/member-table";
import type { Invite, Member, Workspace } from "@/types/api";

type WorkspaceDetailPanelProps = {
  workspace: Workspace;
  loadedMembers: boolean;
  syncing: boolean;
  members: Member[];
  invites: Invite[];
  busyMemberIds: number[];
  inviteActionState: Record<string, "resend" | "revoke">;
  invitePanel: ReactNode;
  onSync: () => void;
  onKick?: (memberId: number) => Promise<void>;
  onResend?: (inviteId: string, email: string) => Promise<void>;
  onRevoke?: (inviteId: string) => Promise<void>;
  includePendingInvitesInLoadGate?: boolean;
};

export function WorkspaceDetailPanel({
  workspace,
  loadedMembers,
  syncing,
  members,
  invites,
  busyMemberIds,
  inviteActionState,
  invitePanel,
  onSync,
  onKick,
  onResend,
  onRevoke,
  includePendingInvitesInLoadGate = false,
}: WorkspaceDetailPanelProps) {
  const hasPreloadedData = Boolean(workspace.last_sync)
    || workspace.member_count > 0
    || (includePendingInvitesInLoadGate && (workspace.pending_invites ?? 0) > 0);

  const pendingInvites = invites.filter((invite) => invite.status === "pending");

  return (
    <div className="workspace-detail">
      {!loadedMembers ? (
        <div className="section-panel section-panel-center">
          <div className="section-heading-row compact-heading-row">
            <div>
              <h3 className="section-heading">
                {syncing
                  ? "Workspace đang đồng bộ dữ liệu"
                  : hasPreloadedData
                    ? "Đang tải chi tiết workspace"
                    : "Workspace data chưa được tải"}
              </h3>
              <p className="section-description">
                {syncing
                  ? "Hệ thống đang sync workspace rồi tải members và invites mới nhất."
                  : hasPreloadedData
                    ? "Đang đọc dữ liệu members và invites đã sync trước đó để hiển thị chi tiết workspace."
                    : "Đồng bộ ngay để lấy danh sách thành viên và lời mời mới nhất từ ChatGPT."}
              </p>
              {workspace.sync_error && (
                <p className="section-description" style={{ color: "#ff8f8f" }}>
                  Lỗi gần nhất: {workspace.sync_error}
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
            {hasPreloadedData || syncing ? (
              <>
                <div className="loading-spinner" />
                <span className="workspace-helper-copy">
                  {syncing
                    ? "Đang đồng bộ và tải chi tiết workspace..."
                    : "Đang tải dữ liệu chi tiết của workspace..."}
                </span>
              </>
            ) : (
              <>
                <button className="btn btn-primary" onClick={onSync} disabled={syncing}>
                  {syncing ? "Đang sync..." : "Sync workspace"}
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
              members={members}
              busyMemberIds={busyMemberIds}
              onKick={onKick}
            />
          </div>

          <div className="workspace-side-column">
            <div className="section-panel invite-section-panel">{invitePanel}</div>

            {pendingInvites.length > 0 ? (
              <div className="section-panel invite-section-panel">
                <InviteList
                  invites={pendingInvites}
                  busyInviteActions={inviteActionState}
                  onResend={onResend}
                  onRevoke={onRevoke}
                />
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
