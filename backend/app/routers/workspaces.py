from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Workspace

router = APIRouter()


@router.get("/api/workspaces")
def get_workspaces(session: Session = Depends(get_session)):
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
def get_workspace_members(id: str):
    return []
