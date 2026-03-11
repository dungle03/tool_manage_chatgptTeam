from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Invite, Member, Workspace
from app.schemas import WorkspaceImportRequest
from app.services.chatgpt import chatgpt_service
from app.services.workspace_sync import (
    build_workspace_list_payload,
    parse_datetime,
    schedule_followup_sync,
    serialize_datetime,
    sync_workspace_data,
)

router = APIRouter()


# Backward-compatible alias used by existing tests.
def _parse_datetime(value):
    return parse_datetime(value)


@router.get("/api/workspaces")
async def get_workspaces(
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    rows = session.execute(select(Workspace).order_by(Workspace.org_id)).scalars().all()
    return build_workspace_list_payload(rows, session)


@router.post("/api/teams/import")
async def import_team(
    payload: WorkspaceImportRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    access_token = payload.access_token
    session_token = payload.session_token

    if not access_token and not session_token:
        raise HTTPException(
            status_code=400,
            detail="access_token or session_token is required",
        )

    if not access_token and session_token:
        try:
            refreshed = await chatgpt_service.refresh_access_token(
                session_token,
                payload.org_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        access_token = refreshed["access_token"]
        session_token = refreshed.get("session_token") or session_token

    try:
        accounts = await chatgpt_service.get_account_info(access_token)
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
            status_code=404,
            detail="no team account found for provided token",
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
            existing.sync_error = None
            existing.member_limit = int(
                info.get("member_limit") or existing.member_limit or 7
            )
            existing.expires_at = parse_datetime(info.get("expires_at"))
            workspace = existing
        else:
            workspace = Workspace(
                org_id=account_id,
                account_id=account_id,
                name=info.get("name") or account_id,
                access_token=access_token,
                session_token=session_token,
                status="live",
                sync_error=None,
                member_count=0,
                member_limit=int(info.get("member_limit") or 7),
                expires_at=parse_datetime(info.get("expires_at")),
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

    imported_org_ids = [item["org_id"] for item in imported]
    for org_id in imported_org_ids:
        workspace = session.execute(
            select(Workspace).where(Workspace.org_id == org_id)
        ).scalar_one_or_none()
        if workspace is not None:
            schedule_followup_sync(
                session,
                workspace,
                reason="workspace_imported",
            )

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
            "invite_date": serialize_datetime(row.invite_date),
            "created_at": serialize_datetime(row.created_at),
            "picture": row.picture,
        }
        for row in rows
    ]


@router.get("/api/workspaces/{id}/sync")
async def sync_workspace(
    id: str,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    schedule_followup_sync(
        session,
        workspace,
        reason="manual_sync",
        delay_seconds=0,
    )

    return await sync_workspace_data(
        session,
        workspace,
        trigger="manual",
        publish_events=True,
    )


@router.delete("/api/workspaces/{id}")
def delete_workspace(
    id: str,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    session.query(Member).where(Member.org_id == workspace.org_id).delete()
    session.query(Invite).where(Invite.org_id == workspace.org_id).delete()
    session.delete(workspace)
    session.commit()

    return {"ok": True, "deleted_org_id": id}
