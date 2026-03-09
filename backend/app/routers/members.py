from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Invite

router = APIRouter()


@router.post("/api/invite")
def invite_member(payload: dict, session: Session = Depends(get_session)):
    org_id = payload.get("org_id")
    email = payload.get("email")
    role = payload.get("role", "member")
    if not org_id or not email:
        raise HTTPException(status_code=400, detail="org_id and email are required")

    invite = Invite(
        org_id=org_id,
        email=email,
        invite_id=f"inv_{uuid4().hex[:10]}",
        status="pending",
        created_at=datetime.utcnow(),
    )
    session.add(invite)
    session.commit()
    return {"ok": True, "invite_id": invite.invite_id, "role": role}


@router.delete("/api/member")
def delete_member(payload: dict):
    return {"ok": True, "payload": payload}
