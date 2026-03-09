from datetime import datetime

from pydantic import BaseModel


# === Response Schemas ===


class WorkspaceOut(BaseModel):
    id: int
    org_id: str
    name: str
    member_limit: int
    created_at: datetime


class MemberOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    status: str
    invite_date: datetime | None


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
    member_id: int


class InviteActionRequest(BaseModel):
    org_id: str
    invite_id: str
