from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Invite
from app.schemas import InviteActionRequest

router = APIRouter()


@router.get("/api/invites")
def get_invites(
    org_id: str,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    rows = (
        session.execute(select(Invite).where(Invite.org_id == org_id)).scalars().all()
    )
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
def resend_invite(
    payload: InviteActionRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    row = session.execute(
        select(Invite).where(
            Invite.org_id == payload.org_id, Invite.invite_id == payload.invite_id
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="invite not found")
    row.status = "pending"
    session.commit()
    return {"ok": True, "status": row.status, "invite_id": row.invite_id}


@router.delete("/api/cancel-invite")
def cancel_invite(
    payload: InviteActionRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    row = session.execute(
        select(Invite).where(
            Invite.org_id == payload.org_id, Invite.invite_id == payload.invite_id
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="invite not found")
    row.status = "cancelled"
    session.commit()
    return {"ok": True, "status": row.status, "invite_id": row.invite_id}
