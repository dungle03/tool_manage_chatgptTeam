import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Invite, Workspace
from app.routers.workspaces import _resolve_access_token
from app.schemas import InviteActionRequest, InviteRequest
from app.services.chatgpt import chatgpt_service

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


@router.post("/api/invite")
def invite_member(
    payload: InviteRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == payload.org_id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    account_id = workspace.account_id or workspace.org_id
    access_token = _resolve_access_token(workspace)

    try:
        response = asyncio.run(
            chatgpt_service.send_invite(
                access_token,
                account_id,
                payload.email,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    invite = Invite(
        org_id=payload.org_id,
        email=payload.email,
        invite_id=str(response.get("id") or f"inv_{uuid4().hex[:10]}"),
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    session.add(invite)
    session.commit()
    return {"ok": True, "invite_id": invite.invite_id, "role": payload.role}


@router.post("/api/resend-invite")
def resend_invite(
    payload: InviteActionRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    row = session.execute(
        select(Invite).where(
            Invite.org_id == payload.org_id,
            Invite.invite_id == payload.invite_id,
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="invite not found")

    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == payload.org_id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    access_token = _resolve_access_token(workspace)
    account_id = workspace.account_id or workspace.org_id

    try:
        asyncio.run(chatgpt_service.send_invite(access_token, account_id, row.email))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

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
            Invite.org_id == payload.org_id,
            Invite.invite_id == payload.invite_id,
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="invite not found")

    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == payload.org_id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    access_token = _resolve_access_token(workspace)
    account_id = workspace.account_id or workspace.org_id

    try:
        asyncio.run(chatgpt_service.delete_invite(access_token, account_id, row.email))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    row.status = "cancelled"
    session.commit()
    return {"ok": True, "status": row.status, "invite_id": row.invite_id}
