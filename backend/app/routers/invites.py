from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Invite

router = APIRouter()


@router.get("/api/invites")
def get_invites(org_id: str, session: Session = Depends(get_session)):
    rows = session.execute(select(Invite).where(Invite.org_id == org_id)).scalars().all()
    return [
        {
            "id": row.id,
            "org_id": row.org_id,
            "email": row.email,
            "invite_id": row.invite_id,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/api/resend-invite")
def resend_invite(payload: dict):
    return {"ok": True, "payload": payload}


@router.delete("/api/cancel-invite")
def cancel_invite(payload: dict):
    return {"ok": True, "payload": payload}
