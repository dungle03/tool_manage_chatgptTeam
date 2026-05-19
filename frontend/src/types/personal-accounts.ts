export type PersonalAccountStatus =
  | "live"
  | "die"
  | "need_relogin"
  | "refreshing"
  | "unknown"
  | "deleted";

export type PersonalAccount = {
  id: number;
  provider: string;
  auth_type: string;
  email: string;
  name: string;
  plan_type: string;
  subscription_plan: string | null;
  plan_expires_at: string | null;
  plan_renews_at: string | null;
  last_plan_sync_at: string | null;
  next_plan_sync_at: string | null;
  plan_sync_error: string | null;
  plan_sync_fail_count: number;
  status: PersonalAccountStatus | string;
  is_active: boolean;
  token_expires_at: string | null;
  last_checked_at: string | null;
  last_refreshed_at: string | null;
  next_refresh_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  oauth_connected: boolean;
  requires_relogin: boolean;
  created_at: string;
  updated_at: string;
};

export type PersonalAccountActionResult = {
  ok: boolean;
  message: string;
  account: PersonalAccount | null;
  next_action: "reconnect" | null;
};

export type PersonalOAuthStart = {
  authorization_url: string;
  state: string;
  expires_in: number;
};

export type PersonalOAuthResult = {
  status: "success" | "duplicate_detected" | "cancelled" | string;
  account: PersonalAccount | null;
  duplicate_token: string | null;
  existing_account: PersonalAccount | null;
  new_account: Record<string, string> | null;
};

export type DuplicateDecision = "overwrite_existing" | "create_new" | "cancel";
