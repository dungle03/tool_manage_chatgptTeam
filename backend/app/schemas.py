from datetime import datetime

from pydantic import BaseModel


# === Response Schemas ===


class WorkspaceOut(BaseModel):
    id: int
    org_id: str
    account_id: str | None = None
    name: str
    status: str
    member_count: int
    member_limit: int
    expires_at: datetime | None = None
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
    created_at: datetime


# === Request Schemas ===


class InviteRequest(BaseModel):
    org_id: str
    email: str
    role: str = "member"


class KickMemberRequest(BaseModel):
    org_id: str
    member_id: int | None = None
    user_id: str | None = None


class WorkspaceImportRequest(BaseModel):
    access_token: str | None = None
    session_token: str | None = None
    org_id: str | None = None
    name: str | None = None


class WorkspaceSyncRequest(BaseModel):
    org_id: str


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
