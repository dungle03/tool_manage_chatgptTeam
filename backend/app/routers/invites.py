from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Invite, Workspace
from app.schemas import InviteActionRequest, InviteRequest
from app.services.chatgpt import chatgpt_service
from app.services.workspace_sync import (
    build_action_response,
    build_refresh_hint,
    normalize_invite_status,
    resolve_access_token,
    schedule_followup_sync,
    serialize_invite_row,
)

router = APIRouter()


async def _refresh_remote_invites_for_workspace(
    session: Session,
    *,
    workspace: Workspace,
    rows: list[Invite],
) -> list[Invite]:
    org_id = workspace.org_id
    rows_by_id = {row.invite_id: row for row in rows if row.invite_id}
    rows_by_email = {row.email.strip().lower(): row for row in rows if row.email}
    seen_row_ids: set[int] = set()

    access_token = await resolve_access_token(workspace)
    account_id = workspace.account_id or workspace.org_id
    remote_invites = await chatgpt_service.get_invites(access_token, account_id)

    for index, item in enumerate(remote_invites, start=1):
        invite_id = str(
            item.get("id") or item.get("invite_id") or f"inv_{org_id}_{index}"
        )
        email = (
            str(item.get("email") or item.get("email_address") or "").strip().lower()
        )
        if not email:
            continue

        existing = rows_by_id.get(invite_id)
        if existing is None:
            existing = rows_by_email.get(email)

        if existing is None:
            existing = Invite(
                org_id=org_id,
                email=email,
                invite_id=invite_id,
                status=normalize_invite_status(item.get("status") or "pending"),
                created_by_tool=False,
                created_at=datetime.now(timezone.utc),
            )
            session.add(existing)
            session.flush()
            rows.append(existing)
        else:
            existing.email = email
            existing.invite_id = invite_id
            existing.status = normalize_invite_status(
                item.get("status") or existing.status or "pending"
            )

        rows_by_id[invite_id] = existing
        rows_by_email[email] = existing
        seen_row_ids.add(existing.id)

    for row in rows:
        if row.id in seen_row_ids:
            continue
        if normalize_invite_status(row.status) == "pending":
            continue
        session.delete(row)

    session.commit()
    return list(
        session.execute(select(Invite).where(Invite.org_id == org_id)).scalars().all()
    )


@router.get("/api/invites")
async def get_invites(
    org_id: str,
    refresh_remote: bool = False,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == org_id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    rows = list(
        session.execute(select(Invite).where(Invite.org_id == org_id)).scalars().all()
    )

    if refresh_remote:
        try:
            rows = await _refresh_remote_invites_for_workspace(
                session,
                workspace=workspace,
                rows=rows,
            )
        except Exception:
            session.rollback()
            rows = list(
                session.execute(select(Invite).where(Invite.org_id == org_id))
                .scalars()
                .all()
            )

    return [serialize_invite_row(row) for row in rows]


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
    normalized_email = payload.email.strip().lower()

    existing_invite_candidates = (
        session.execute(
            select(Invite)
            .where(
                Invite.org_id == payload.org_id,
                Invite.email.ilike(normalized_email),
            )
            .order_by(Invite.created_at.desc())
        )
        .scalars()
        .all()
    )
    existing_invite = next(
        (
            invite
            for invite in existing_invite_candidates
            if normalize_invite_status(invite.status) == "pending"
        ),
        None,
    )
    if existing_invite:
        if not existing_invite.created_by_tool:
            existing_invite.created_by_tool = True
            session.flush()
        invite_payload = serialize_invite_row(existing_invite)
        return build_action_response(
            action="invite_create",
            workspace=workspace,
            session=session,
            updated_record=invite_payload,
            refresh_hint=build_refresh_hint(
                scope="workspace_detail",
                org_id=workspace.org_id,
                reason="invite_already_pending",
                include_details=True,
            ),
            extra={
                "invite_id": invite_payload["invite_id"],
                "role": payload.role,
                "invite": invite_payload,
                "already_pending": True,
            },
        )

    try:
        response = await chatgpt_service.send_invite(
            access_token,
            account_id,
            normalized_email,
            resend_emails=False,
        )

        remote_invite_id = response.get("id")
        if not remote_invite_id:
            invites = await chatgpt_service.get_invites(access_token, account_id)
            matched_invite = next(
                (
                    item
                    for item in invites
                    if str(item.get("email") or item.get("email_address") or "")
                    .strip()
                    .lower()
                    == normalized_email
                    and str(item.get("status", "pending")).strip().lower() == "pending"
                ),
                None,
            )
            remote_invite_id = matched_invite.get("id") if matched_invite else None
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"failed to create invite upstream: {exc}",
        ) from exc

    invite_id_value = str(remote_invite_id or normalized_email)
    invite = None
    if remote_invite_id:
        invite = session.execute(
            select(Invite).where(Invite.invite_id == invite_id_value)
        ).scalar_one_or_none()

    if invite is None:
        invite = session.execute(
            select(Invite).where(
                Invite.org_id == payload.org_id,
                or_(
                    Invite.email == normalized_email,
                    Invite.invite_id == invite_id_value,
                ),
            )
        ).scalar_one_or_none()

    if invite is None:
        invite = Invite(
            org_id=payload.org_id,
            email=normalized_email,
            invite_id=invite_id_value,
            status="pending",
            created_by_tool=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(invite)
    else:
        invite.org_id = payload.org_id
        invite.email = normalized_email
        invite.invite_id = invite_id_value
        invite.status = "pending"
        invite.created_by_tool = True
    session.flush()
    invite_payload = serialize_invite_row(invite)
    schedule_followup_sync(
        session,
        workspace,
        reason="invite_created",
    )
    session.commit()
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
            "invite_id": invite_payload["invite_id"],
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
    if not row and payload.email:
        normalized_email = payload.email.strip().lower()
        row = session.execute(
            select(Invite).where(
                Invite.org_id == payload.org_id,
                Invite.email.ilike(normalized_email),
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
    invite_id = row.invite_id
    updated_record = serialize_invite_row(row)
    updated_record["status"] = "pending"

    try:
        await chatgpt_service.send_invite(access_token, account_id, row.email)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"failed to resend invite upstream: {exc}",
        ) from exc

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
        updated_record=updated_record,
        refresh_hint=build_refresh_hint(
            scope="workspace_detail",
            org_id=workspace.org_id,
            reason="invite_resend",
            include_details=True,
        ),
        extra={"status": "pending", "invite_id": invite_id},
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
    invite_id = row.invite_id
    updated_record = serialize_invite_row(row)
    updated_record["status"] = "cancelled"

    try:
        await chatgpt_service.delete_invite(
            access_token,
            account_id,
            invite_id=row.invite_id,
            email=row.email,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"failed to cancel invite upstream: {exc}",
        ) from exc

    session.delete(row)
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
        updated_record=updated_record,
        refresh_hint=build_refresh_hint(
            scope="workspace_detail",
            org_id=workspace.org_id,
            reason="invite_cancelled",
            include_details=True,
        ),
        extra={"status": "cancelled", "invite_id": invite_id},
    )
