from pydantic import BaseModel


class WorkspaceOut(BaseModel):
    id: int
    org_id: str
    name: str
    member_limit: int
    created_at: str


class MemberOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    status: str
    invite_date: str | None


class InviteOut(BaseModel):
    id: int
    org_id: str
    email: str
    invite_id: str
    status: str
    created_at: str
