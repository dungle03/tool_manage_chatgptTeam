import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Invite, Member, Workspace
from app.services.chatgpt import chatgpt_service

router = APIRouter()


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _resolve_access_token(workspace: Workspace) -> str:
    account_id = workspace.account_id or workspace.org_id

    if workspace.session_token:
        try:
            refreshed = asyncio.run(
                chatgpt_service.refresh_access_token(
                    workspace.session_token,
                    account_id,
                )
            )
            workspace.access_token = refreshed["access_token"]
            workspace.session_token = refreshed.get("session_token") or workspace.session_token
            return workspace.access_token
        except Exception:
            if workspace.access_token:
                return workspace.access_token
            raise

    if workspace.access_token:
        return workspace.access_token

    raise HTTPException(status_code=400, detail="workspace missing access/session token")


@router.get("/api/workspaces")
def get_workspaces(
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    rows = session.execute(select(Workspace).order_by(Workspace.org_id)).scalars().all()
    return [
        {
            "id": row.id,
            "org_id": row.org_id,
            "account_id": row.account_id,
            "name": row.name,
            "status": row.status,
            "member_count": row.member_count,
            "member_limit": row.member_limit,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "last_sync": row.last_sync.isoformat() if row.last_sync else None,
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
            "remote_id": row.remote_id,
            "name": row.name,
            "email": row.email,
            "role": row.role,
            "status": row.status,
            "invite_date": row.invite_date.isoformat() if row.invite_date else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "picture": row.picture,
        }
        for row in rows
    ]


@router.get("/api/workspaces/{id}/sync")
def sync_workspace(
    id: str,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(select(Workspace).where(Workspace.org_id == id)).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    account_id = workspace.account_id or workspace.org_id

    try:
        access_token = _resolve_access_token(workspace)
        remote_members = asyncio.run(chatgpt_service.get_members(access_token, account_id))
        remote_invites = asyncio.run(chatgpt_service.get_invites(access_token, account_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    session.query(Member).where(Member.org_id == workspace.org_id).delete()
    session.query(Invite).where(Invite.org_id == workspace.org_id).delete()

    for item in remote_members:
        created = _parse_datetime(item.get("created") or item.get("created_at"))
        session.add(
            Member(
                org_id=workspace.org_id,
                remote_id=str(item.get("id") or "") or None,
                email=item.get("email") or "",
                name=item.get("name") or "",
                role=item.get("role") or "member",
                status=item.get("status") or "active",
                invite_date=created,
                created_at=created,
                picture=item.get("picture"),
            )
        )

    for item in remote_invites:
        created_at = _parse_datetime(item.get("created_at") or item.get("created"))
        session.add(
            Invite(
                org_id=workspace.org_id,
                email=item.get("email") or item.get("email_address") or "",
                invite_id=str(item.get("id") or item.get("invite_id") or f"inv_{workspace.org_id}_{len(remote_invites)}"),
                status=item.get("status") or "pending",
                created_at=created_at or datetime.now(timezone.utc),
            )
        )

    workspace.member_count = len(remote_members)
    workspace.last_sync = datetime.now(timezone.utc)
    workspace.status = "live"
    session.commit()

    return {
        "ok": True,
        "members_synced": len(remote_members),
        "invites_synced": len(remote_invites),
        "last_sync": workspace.last_sync.isoformat(),
    }
