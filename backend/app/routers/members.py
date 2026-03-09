from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Invite, Member
from app.schemas import InviteRequest, KickMemberRequest

router = APIRouter()


@router.post("/api/invite")
def invite_member(
    payload: InviteRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    invite = Invite(
        org_id=payload.org_id,
        email=payload.email,
        invite_id=f"inv_{uuid4().hex[:10]}",
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    session.add(invite)
    session.commit()
    return {"ok": True, "invite_id": invite.invite_id, "role": payload.role}


@router.delete("/api/member")
def delete_member(
    payload: KickMemberRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    row = session.execute(
        select(Member).where(
            Member.org_id == payload.org_id, Member.id == payload.member_id
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="member not found")
    if row.role.lower() == "owner":
        raise HTTPException(status_code=409, detail="cannot remove owner")
    row.status = "removed"
    session.commit()
    return {"ok": True, "member_id": row.id, "status": row.status}
