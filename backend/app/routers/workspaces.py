from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Invite, Member, UnauthorizedFinding, Workspace
from app.schemas import (
    UnauthorizedFindingActionRequest,
    WorkspaceImportRequest,
    WorkspacePolicyUpdateRequest,
    WorkspaceRenameRequest,
    WorkspaceTokenUpdateRequest,
)
from app.services.chatgpt import chatgpt_service
from app.services.workspace_sync import (
    build_action_response,
    build_refresh_hint,
    build_sync_in_progress_payload,
    build_workspace_list_payload,
    is_workspace_sync_in_progress,
    parse_datetime,
    resolve_access_token,
    schedule_followup_sync,
    serialize_datetime,
    serialize_unauthorized_finding_row,
    sync_workspace_data,
    workspace_to_dict,
)

router = APIRouter()


# Backward-compatible alias used by existing tests.
def _parse_datetime(value):
    return parse_datetime(value)


def _normalize_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"off", "warn_only", "auto_kick"}:
        raise HTTPException(
            status_code=400,
            detail="unauthorized_member_mode must be one of: off, warn_only, auto_kick",
        )
    return normalized


def _finding_by_id(
    session: Session, org_id: str, finding_id: int
) -> UnauthorizedFinding:
    finding = session.execute(
        select(UnauthorizedFinding).where(
            UnauthorizedFinding.org_id == org_id,
            UnauthorizedFinding.id == finding_id,
        )
    ).scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=404, detail="unauthorized finding not found")
    return finding


@router.get("/api/workspaces")
async def get_workspaces(
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    rows = list(
        session.execute(select(Workspace).order_by(Workspace.org_id)).scalars().all()
    )
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
            raise HTTPException(
                status_code=502,
                detail=f"failed to refresh access token: {exc}",
            ) from exc
        access_token = str(refreshed["access_token"])
        session_token = refreshed.get("session_token") or session_token

    if access_token is None:
        raise HTTPException(status_code=400, detail="access token is required")

    try:
        accounts = await chatgpt_service.get_account_info(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"failed to load team accounts: {exc}",
        ) from exc

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

    imported_workspaces: list[Workspace] = []
    for info in accounts:
        account_id = str(info.get("account_id") or "")
        if not account_id:
            continue

        existing = session.execute(
            select(Workspace).where(Workspace.org_id == account_id)
        ).scalar_one_or_none()

        workspace_name = str(info.get("name") or account_id)

        if existing:
            existing.account_id = account_id
            existing.name = workspace_name
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
                name=workspace_name,
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

        imported_workspaces.append(workspace)

    if not imported_workspaces:
        raise HTTPException(status_code=502, detail="unable to import team workspace")

    session.flush()
    imported = [
        {
            "id": workspace.id,
            "org_id": workspace.org_id,
            "name": workspace.name,
        }
        for workspace in imported_workspaces
    ]
    imported_org_ids = [str(item["org_id"]) for item in imported]
    session.commit()

    schedule_warnings: list[dict[str, str]] = []
    for org_id in imported_org_ids:
        try:
            workspace = session.execute(
                select(Workspace).where(Workspace.org_id == org_id)
            ).scalar_one_or_none()
            if workspace is None:
                continue

            schedule_followup_sync(
                session,
                workspace,
                reason="workspace_imported",
            )
            session.commit()
        except Exception as exc:
            session.rollback()
            schedule_warnings.append(
                {
                    "org_id": org_id,
                    "message": f"failed to schedule follow-up sync: {exc}",
                }
            )

    refreshed_workspaces = list(
        session.execute(
            select(Workspace)
            .where(Workspace.org_id.in_(imported_org_ids))
            .order_by(Workspace.org_id)
        )
        .scalars()
        .all()
    )
    imported_payload = build_workspace_list_payload(refreshed_workspaces, session)
    return build_action_response(
        action="workspace_import",
        refresh_hint=build_refresh_hint(
            scope="workspace_list",
            reason="workspace_imported",
            include_details=False,
        ),
        extra={
            "imported": imported,
            "updated_records": imported_payload,
            "schedule_warnings": schedule_warnings,
        },
    )


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


@router.get("/api/unauthorized-findings")
def get_all_unauthorized_findings(
    include_resolved: bool = False,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    """Return global unauthorized findings, active-only by default, enriched with workspace name."""
    workspace_names: dict[str, str] = {}
    for ws in session.execute(select(Workspace)).scalars().all():
        workspace_names[ws.org_id] = ws.name

    statement = select(UnauthorizedFinding)
    if not include_resolved:
        statement = statement.where(
            UnauthorizedFinding.status.in_(("detected", "kick_failed"))
        )

    rows = (
        session.execute(
            statement.order_by(
                UnauthorizedFinding.last_seen_at.desc(),
                UnauthorizedFinding.id.desc(),
            )
        )
        .scalars()
        .all()
    )
    results = []
    for row in rows:
        serialized = serialize_unauthorized_finding_row(row)
        serialized["workspace_name"] = workspace_names.get(row.org_id, row.org_id)
        results.append(serialized)
    return results


@router.get("/api/workspaces/{id}/unauthorized-members")
def get_unauthorized_members(
    id: str,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    rows = (
        session.execute(
            select(UnauthorizedFinding)
            .where(UnauthorizedFinding.org_id == id)
            .order_by(
                case(
                    (UnauthorizedFinding.status == "detected", 0),
                    (UnauthorizedFinding.status == "kick_failed", 1),
                    else_=2,
                ),
                UnauthorizedFinding.last_seen_at.desc(),
                UnauthorizedFinding.id.desc(),
            )
        )
        .scalars()
        .all()
    )
    return [serialize_unauthorized_finding_row(row) for row in rows]


@router.post("/api/workspaces/{id}/sync")
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

    if is_workspace_sync_in_progress(workspace.org_id):
        schedule_followup_sync(
            session,
            workspace,
            reason="manual_sync",
            delay_seconds=0,
        )
        session.commit()
        return build_sync_in_progress_payload(workspace, session)

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


@router.patch("/api/workspaces/{id}/unauthorized-policy")
async def update_unauthorized_policy(
    id: str,
    payload: WorkspacePolicyUpdateRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    workspace.unauthorized_member_mode = _normalize_mode(
        payload.unauthorized_member_mode
    )
    session.commit()
    session.refresh(workspace)

    return build_action_response(
        action="workspace_policy_update",
        workspace=workspace,
        session=session,
        refresh_hint=build_refresh_hint(
            scope="workspace_detail",
            org_id=workspace.org_id,
            reason="workspace_policy_updated",
            include_details=True,
        ),
        extra={"unauthorized_member_mode": workspace.unauthorized_member_mode},
    )


@router.post("/api/workspaces/{id}/unauthorized-members/{finding_id}/trust")
async def trust_unauthorized_member(
    id: str,
    finding_id: int,
    payload: UnauthorizedFindingActionRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == id)
    ).scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail="workspace not found")

    finding = _finding_by_id(session, id, finding_id)
    now = datetime.now(timezone.utc)
    finding.status = "trusted"
    finding.action_reason = payload.reason or "manually_trusted"
    finding.resolved_at = now
    finding.updated_at = now
    session.commit()
    session.refresh(finding)
    session.refresh(workspace)

    return build_action_response(
        action="unauthorized_member_trust",
        workspace=workspace,
        session=session,
        updated_record=serialize_unauthorized_finding_row(finding),
        refresh_hint=build_refresh_hint(
            scope="workspace_detail",
            org_id=id,
            reason="unauthorized_member_trusted",
            include_details=True,
        ),
        extra={"finding_id": finding.id, "status": finding.status},
    )


@router.post("/api/workspaces/{id}/unauthorized-members/{finding_id}/kick")
async def kick_unauthorized_member(
    id: str,
    finding_id: int,
    payload: UnauthorizedFindingActionRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == id)
    ).scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail="workspace not found")

    finding = _finding_by_id(session, id, finding_id)
    if not finding.remote_id:
        raise HTTPException(
            status_code=409, detail="unauthorized finding has no remote member id"
        )
    if finding.role.lower() == "owner":
        raise HTTPException(status_code=409, detail="cannot remove owner")

    access_token = await resolve_access_token(workspace)
    account_id = workspace.account_id or workspace.org_id

    try:
        await chatgpt_service.delete_member(access_token, account_id, finding.remote_id)
    except Exception as exc:
        now = datetime.now(timezone.utc)
        finding.status = "kick_failed"
        finding.action_reason = str(exc)
        finding.updated_at = now
        finding.resolved_at = None
        session.commit()
        raise HTTPException(
            status_code=502,
            detail=f"failed to remove unauthorized member upstream: {exc}",
        ) from exc

    local_member = session.execute(
        select(Member).where(
            Member.org_id == id,
            Member.remote_id == finding.remote_id,
        )
    ).scalar_one_or_none()
    if local_member is not None:
        session.delete(local_member)
        if workspace.member_count > 0:
            workspace.member_count -= 1

    now = datetime.now(timezone.utc)
    finding.status = "kicked"
    finding.action_reason = payload.reason or "manual_kick"
    finding.resolved_at = now
    finding.updated_at = now
    schedule_followup_sync(session, workspace, reason="member_kicked")
    session.commit()
    session.refresh(finding)
    session.refresh(workspace)

    return build_action_response(
        action="unauthorized_member_kick",
        workspace=workspace,
        session=session,
        updated_record=serialize_unauthorized_finding_row(finding),
        refresh_hint=build_refresh_hint(
            scope="workspace_detail",
            org_id=id,
            reason="unauthorized_member_kicked",
            include_details=True,
        ),
        extra={"finding_id": finding.id, "status": finding.status},
    )


@router.patch("/api/workspaces/{id}/name")
async def rename_workspace(
    id: str,
    payload: WorkspaceRenameRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    next_name = " ".join(payload.name.split()).strip()
    if not next_name:
        raise HTTPException(status_code=400, detail="workspace name is required")
    if len(next_name) > 120:
        raise HTTPException(
            status_code=400, detail="workspace name must be 120 characters or fewer"
        )

    access_token = workspace.access_token
    session_token = workspace.session_token

    if not access_token and not session_token:
        raise HTTPException(
            status_code=400,
            detail="workspace does not have an access token or session token",
        )

    if not access_token and session_token:
        try:
            refreshed = await chatgpt_service.refresh_access_token(
                session_token,
                workspace.account_id or workspace.org_id,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"failed to refresh access token: {exc}",
            ) from exc
        access_token = refreshed["access_token"]
        workspace.access_token = access_token
        workspace.session_token = refreshed.get("session_token") or session_token

    if access_token is None:
        raise HTTPException(
            status_code=400, detail="workspace access token is required"
        )

    try:
        await chatgpt_service.rename_workspace(
            access_token,
            workspace.account_id or workspace.org_id,
            next_name,
        )
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"failed to rename workspace upstream: {exc}",
        ) from exc

    workspace.name = next_name
    workspace.status = "live"
    workspace.sync_error = None
    session.commit()
    session.refresh(workspace)

    return build_action_response(
        action="workspace_rename",
        workspace=workspace,
        session=session,
        refresh_hint=build_refresh_hint(
            scope="workspace_list",
            org_id=workspace.org_id,
            reason="workspace_renamed",
            include_details=False,
        ),
        extra={"name": workspace.name},
    )


@router.patch("/api/workspaces/{id}/token")
async def update_workspace_token(
    id: str,
    payload: WorkspaceTokenUpdateRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    access_token = payload.access_token.strip()
    if not access_token:
        raise HTTPException(status_code=400, detail="access token is required")

    try:
        accounts = await chatgpt_service.get_account_info(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"failed to validate access token: {exc}",
        ) from exc

    account_ids = {
        str(account.get("account_id") or "")
        for account in accounts
        if str(account.get("account_id") or "")
    }
    expected_account_id = workspace.account_id or workspace.org_id
    if account_ids and expected_account_id not in account_ids:
        raise HTTPException(
            status_code=400,
            detail="token does not belong to this workspace",
        )

    try:
        chatgpt_service.decode_access_token_claims(access_token)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"invalid access token: {exc}",
        ) from exc

    workspace.access_token = access_token
    workspace.status = "live"
    workspace.sync_error = None
    session.commit()
    session.refresh(workspace)

    return build_action_response(
        action="workspace_token_update",
        workspace=workspace,
        session=session,
        refresh_hint=build_refresh_hint(
            scope="workspace_list",
            org_id=workspace.org_id,
            reason="workspace_token_updated",
            include_details=False,
        ),
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

    deleted_summary = workspace_to_dict(workspace, session)
    session.query(Member).where(Member.org_id == workspace.org_id).delete()
    session.query(Invite).where(Invite.org_id == workspace.org_id).delete()
    session.query(UnauthorizedFinding).where(
        UnauthorizedFinding.org_id == workspace.org_id
    ).delete()
    session.delete(workspace)
    session.commit()

    return build_action_response(
        action="workspace_delete",
        updated_summary=deleted_summary,
        refresh_hint=build_refresh_hint(
            scope="workspace_list",
            org_id=id,
            reason="workspace_deleted",
            include_details=False,
        ),
        extra={"deleted_org_id": id},
    )
