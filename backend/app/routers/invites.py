from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Invite, Workspace
from app.schemas import InviteActionRequest, InviteOut, InviteRequest
from app.services.chatgpt import chatgpt_service
from app.services.workspace_sync import (
    build_action_response,
    build_refresh_hint,
    resolve_access_token,
    schedule_followup_sync,
    serialize_invite_row,
)

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
async def invite_member(
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
    access_token = await resolve_access_token(workspace)

    try:
        response = await chatgpt_service.send_invite(
            access_token,
            account_id,
            payload.email,
        )

        remote_invite_id = response.get("id")
        if not remote_invite_id:
            invites = await chatgpt_service.get_invites(access_token, account_id)
            matched_invite = next(
                (
                    item
                    for item in invites
                    if str(item.get("email", "")).strip().lower() == payload.email.strip().lower()
                    and str(item.get("status", "pending")).strip().lower() == "pending"
                ),
                None,
            )
            remote_invite_id = matched_invite.get("id") if matched_invite else None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    invite = Invite(
        org_id=payload.org_id,
        email=payload.email,
        invite_id=str(remote_invite_id or payload.email.strip().lower()),
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    session.add(invite)
    schedule_followup_sync(
        session,
        workspace,
        reason="invite_created",
    )
    session.commit()
    session.refresh(invite)
    invite_payload = serialize_invite_row(invite)
    return build_action_response(
        action="invite_create",
        workspace=workspace,
        session=session,
        updated_record=invite_payload,
        refresh_hint=build_refresh_hint(
            scope="workspace_detail",
            org_id=workspace.org_id,
            reason="invite_created",
            include_details=True,
        ),
        extra={
            "invite_id": invite.invite_id,
            "role": payload.role,
            "invite": invite_payload,
        },
    )


@router.post("/api/resend-invite")
async def resend_invite(
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

    access_token = await resolve_access_token(workspace)
    account_id = workspace.account_id or workspace.org_id

    try:
        await chatgpt_service.send_invite(access_token, account_id, row.email)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    row.status = "pending"
    schedule_followup_sync(
        session,
        workspace,
        reason="invite_resend",
    )
    session.commit()
    return build_action_response(
        action="invite_resend",
        workspace=workspace,
        session=session,
        updated_record=serialize_invite_row(row),
        refresh_hint=build_refresh_hint(
            scope="workspace_detail",
            org_id=workspace.org_id,
            reason="invite_resend",
            include_details=True,
        ),
        extra={"status": row.status, "invite_id": row.invite_id},
    )


@router.delete("/api/cancel-invite")
async def cancel_invite(
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

    access_token = await resolve_access_token(workspace)
    account_id = workspace.account_id or workspace.org_id

    try:
        await chatgpt_service.delete_invite(
            access_token,
            account_id,
            invite_id=row.invite_id,
            email=row.email,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    row.status = "cancelled"
    schedule_followup_sync(
        session,
        workspace,
        reason="invite_cancelled",
    )
    session.commit()
    return build_action_response(
        action="invite_cancel",
        workspace=workspace,
        session=session,
        updated_record=serialize_invite_row(row),
        refresh_hint=build_refresh_hint(
            scope="workspace_detail",
            org_id=workspace.org_id,
            reason="invite_cancelled",
            include_details=True,
        ),
        extra={"status": row.status, "invite_id": row.invite_id},
    )
