export type UnauthorizedMemberMode = "off" | "warn_only" | "auto_kick";
export type UnauthorizedFindingStatus =
  | "detected"
  | "kicked"
  | "kick_failed"
  | "trusted";

export type UnauthorizedFinding = {
  id: number;
  org_id: string;
  remote_id: string | null;
  email: string;
  name: string;
  role: string;
  status: UnauthorizedFindingStatus;
  detection_reason: string;
  action_reason: string | null;
  first_seen_at: string;
  last_seen_at: string;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Workspace = {
  id: number;
  org_id: string;
  account_id: string | null;
  name: string;
  status: string;
  member_count: number;
  member_limit: number;
  pending_invites?: number;
  unauthorized_member_mode?: UnauthorizedMemberMode;
  unauthorized_active_count?: number;
  unauthorized_last_detected_at?: string | null;
  expires_at: string | null;
  access_token_expires_at?: string | null;
  last_sync: string | null;
  created_at: string;
  current_user_role: string;
  can_manage_members: boolean;
  sync_error?: string | null;
  sync_started_at?: string | null;
  sync_finished_at?: string | null;
  next_sync_at?: string | null;
  hot_until?: string | null;
  last_activity_at?: string | null;
  sync_reason?: string | null;
  sync_priority?: number;
  is_hot?: boolean;
};

export type WorkspaceEvent = {
  type:
    | "sync_started"
    | "workspace_updated"
    | "sync_failed"
    | "workspace_scheduled"
    | "heartbeat";
  org_id?: string;
  timestamp: string;
  sequence: number;
  trigger?: "manual" | "auto";
  reason?: string;
  next_sync_at?: string | null;
  hot_until?: string | null;
  is_hot?: boolean;
  pending_invites?: number;
  priority?: number;
  summary?: {
    member_count: number;
    pending_invites: number;
    unauthorized_active_count?: number;
    status: string;
    last_sync: string | null;
  };
  error?: {
    message: string;
  };
};

export type Member = {
  id: number;
  remote_id: string | null;
  name: string;
  email: string;
  role: string;
  status: string;
  invite_date: string | null;
  created_at: string | null;
  picture: string | null;
};

export type Invite = {
  id: number;
  org_id: string;
  email: string;
  invite_id: string;
  status: string;
  created_at: string;
};

export type RefreshHint = {
  scope: "workspace_detail" | "workspace_list";
  reason: string;
  org_id?: string;
  include_details: boolean;
};

export type MutationResult<TRecord = unknown, TSummary = Workspace> = {
  ok: boolean;
  action?: string;
  updated_record?: TRecord;
  updated_summary?: TSummary;
  refresh_hint?: RefreshHint;
  [key: string]: unknown;
};

export type InviteMutationResult = MutationResult<Invite> & {
  invite_id?: string;
  invite?: Invite;
  role?: string;
};

export type MemberMutationResult = MutationResult<Member> & {
  member_id?: number;
  status?: string;
};

export type UnauthorizedFindingMutationResult = MutationResult<UnauthorizedFinding> & {
  finding_id?: number;
  status?: UnauthorizedFindingStatus;
};

export type WorkspaceImportResult = MutationResult<Workspace[]> & {
  imported: { id: number; org_id: string; name: string }[];
  updated_records?: Workspace[];
  schedule_warnings?: { org_id: string; message: string }[];
};

export type WorkspaceSyncResult = MutationResult<never> & {
  already_in_progress?: boolean;
  members_synced: number;
  invites_synced: number;
  last_sync: string | null;
  unauthorized_detected?: number;
  unauthorized_kicked?: number;
};

export type WorkspaceDeleteResult = MutationResult<never> & {
  deleted_org_id: string;
};

export type WorkspaceRenameResult = MutationResult<never> & {
  name: string;
};

export type WorkspaceTokenUpdateResult = MutationResult<never>;

export type WorkspacePolicyUpdateResult = MutationResult<never> & {
  unauthorized_member_mode: UnauthorizedMemberMode;
};
