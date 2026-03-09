from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Member, Workspace

router = APIRouter()


@router.get("/api/workspaces")
def get_workspaces(
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    rows = session.execute(select(Workspace)).scalars().all()
    return [
        {
            "id": row.id,
            "org_id": row.org_id,
            "name": row.name,
            "member_limit": row.member_limit,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/api/workspaces/{id}/members")
def get_workspace_members(
    id: str,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    rows = session.execute(select(Member).where(Member.org_id == id)).scalars().all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "role": row.role,
            "status": row.status,
            "invite_date": row.invite_date.isoformat() if row.invite_date else None,
        }
        for row in rows
    ]
