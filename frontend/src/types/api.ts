export type Workspace = {
  id: number;
  org_id: string;
  account_id: string | null;
  name: string;
  status: string;
  member_count: number;
  member_limit: number;
  pending_invites?: number;
  expires_at: string | null;
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
