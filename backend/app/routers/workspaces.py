import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Invite, Member, Workspace
from app.schemas import WorkspaceImportRequest
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
            workspace.session_token = (
                refreshed.get("session_token") or workspace.session_token
            )
            return workspace.access_token
        except Exception:
            if workspace.access_token:
                return workspace.access_token
            raise

    if workspace.access_token:
        return workspace.access_token

    raise HTTPException(
        status_code=400, detail="workspace missing access/session token"
    )


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


@router.post("/api/teams/import")
def import_team(
    payload: WorkspaceImportRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    access_token = payload.access_token
    session_token = payload.session_token

    if not access_token and not session_token:
        raise HTTPException(
            status_code=400, detail="access_token or session_token is required"
        )

    if not access_token and session_token:
        try:
            refreshed = asyncio.run(
                chatgpt_service.refresh_access_token(session_token, payload.org_id)
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        access_token = refreshed["access_token"]
        session_token = refreshed.get("session_token") or session_token

    try:
        accounts = asyncio.run(chatgpt_service.get_account_info(access_token))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not accounts and payload.org_id and payload.name:
        accounts = [
            {
                "account_id": payload.org_id,
                "name": payload.name,
                "member_limit": 7,
                "expires_at": None,
            }
        ]

    if not accounts:
        raise HTTPException(
            status_code=404, detail="no team account found for provided token"
        )

    imported = []
    for info in accounts:
        account_id = str(info.get("account_id") or "")
        if not account_id:
            continue

        existing = session.execute(
            select(Workspace).where(Workspace.org_id == account_id)
        ).scalar_one_or_none()

        if existing:
            existing.account_id = account_id
            existing.name = info.get("name") or existing.name
            existing.access_token = access_token
            existing.session_token = session_token
            existing.status = "live"
            existing.member_limit = int(
                info.get("member_limit") or existing.member_limit or 7
            )
            existing.expires_at = _parse_datetime(info.get("expires_at"))
            workspace = existing
        else:
            workspace = Workspace(
                org_id=account_id,
                account_id=account_id,
                name=info.get("name") or account_id,
                access_token=access_token,
                session_token=session_token,
                status="live",
                member_count=0,
                member_limit=int(info.get("member_limit") or 7),
                expires_at=_parse_datetime(info.get("expires_at")),
                last_sync=None,
            )
            session.add(workspace)
            session.flush()

        imported.append(
            {
                "id": workspace.id,
                "org_id": workspace.org_id,
                "name": workspace.name,
            }
        )

    if not imported:
        raise HTTPException(status_code=502, detail="unable to import team workspace")

    session.commit()
    return {"ok": True, "imported": imported}


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
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    account_id = workspace.account_id or workspace.org_id

    try:
        access_token = _resolve_access_token(workspace)
        remote_members = asyncio.run(
            chatgpt_service.get_members(access_token, account_id)
        )
        remote_invites = asyncio.run(
            chatgpt_service.get_invites(access_token, account_id)
        )
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

    for index, item in enumerate(remote_invites, start=1):
        created_at = _parse_datetime(item.get("created_at") or item.get("created"))
        session.add(
            Invite(
                org_id=workspace.org_id,
                email=item.get("email") or item.get("email_address") or "",
                invite_id=str(
                    item.get("id")
                    or item.get("invite_id")
                    or f"inv_{workspace.org_id}_{index}"
                ),
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
