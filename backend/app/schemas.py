from datetime import datetime

from pydantic import BaseModel


class WorkspaceOut(BaseModel):
    id: int
    org_id: str
    account_id: str | None = None
    name: str
    status: str
    member_count: int
    member_limit: int
    expires_at: datetime | None = None
    access_token_expires_at: datetime | None = None
    last_sync: datetime | None = None
    created_at: datetime


class WorkspaceSyncOut(BaseModel):
    ok: bool
    members_synced: int
    invites_synced: int
    last_sync: datetime


class MemberOut(BaseModel):
    id: int
    remote_id: str | None = None
    name: str
    email: str
    role: str
    status: str
    invite_date: datetime | None
    created_at: datetime | None = None
    picture: str | None = None


class InviteOut(BaseModel):
    id: int
    org_id: str
    email: str
    invite_id: str
    status: str
    created_by_tool: bool = False
    created_at: datetime


class UnauthorizedFindingOut(BaseModel):
    id: int
    org_id: str
    remote_id: str | None = None
    email: str
    name: str
    role: str
    status: str
    detection_reason: str
    action_reason: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InviteRequest(BaseModel):
    org_id: str
    email: str
    role: str = "member"


class KickMemberRequest(BaseModel):
    org_id: str
    member_id: int | None = None
    user_id: str | None = None


class WorkspaceImportRequest(BaseModel):
    access_token: str
    org_id: str | None = None
    name: str | None = None


class WorkspaceRenameRequest(BaseModel):
    name: str


class WorkspaceTokenUpdateRequest(BaseModel):
    access_token: str


class WorkspaceSyncRequest(BaseModel):
    org_id: str


class WorkspacePolicyUpdateRequest(BaseModel):
    unauthorized_member_mode: str


class UnauthorizedFindingActionRequest(BaseModel):
    reason: str | None = None


class CancelInviteRequest(BaseModel):
    org_id: str
    invite_id: str | None = None
    email: str | None = None


class DeleteInviteRequest(BaseModel):
    org_id: str
    email: str


class DeleteMemberByUserRequest(BaseModel):
    org_id: str
    user_id: str


class InviteActionRequest(BaseModel):
    org_id: str
    invite_id: str
    email: str | None = None


class PersonalAccountOut(BaseModel):
    id: int
    provider: str
    auth_type: str
    email: str
    name: str
    plan_type: str
    subscription_plan: str | None = None
    plan_expires_at: datetime | None = None
    plan_renews_at: datetime | None = None
    last_plan_sync_at: datetime | None = None
    next_plan_sync_at: datetime | None = None
    plan_sync_error: str | None = None
    plan_sync_fail_count: int = 0
    status: str
    is_active: bool
    token_expires_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_refreshed_at: datetime | None = None
    next_refresh_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    oauth_connected: bool
    requires_relogin: bool
    created_at: datetime
    updated_at: datetime


class PersonalAccountActionOut(BaseModel):
    ok: bool
    message: str
    account: PersonalAccountOut | None = None
    next_action: str | None = None


class PersonalAccountDuplicateOut(BaseModel):
    ok: bool = False
    code: str = "duplicate_detected"
    message: str = "Account already exists"
    duplicate_token: str
    duplicate: PersonalAccountOut
    pending_account: dict[str, str] | None = None
    options: list[str] = ["overwrite_existing", "create_new", "cancel"]


class PersonalOAuthStartOut(BaseModel):
    authorization_url: str
    state: str
    expires_in: int


class PersonalOAuthCallbackUrlRequest(BaseModel):
    callback_url: str


class PersonalOAuthDuplicateResolveRequest(BaseModel):
    duplicate_token: str
    decision: str


class PersonalOAuthResultOut(BaseModel):
    status: str
    account: PersonalAccountOut | None = None
    duplicate_token: str | None = None
    existing_account: PersonalAccountOut | None = None
    new_account: dict[str, str] | None = None
