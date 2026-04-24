from datetime import datetime
from typing import Any

from jwt import PyJWTError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Invite, Member, Workspace
from app.services.chatgpt import chatgpt_service
from app.services.workspace_datetime import coerce_utc, serialize_datetime, utc_now
from app.services.workspace_unauthorized import (
    active_unauthorized_count as get_unauthorized_active_count,
    build_unauthorized_count_map as unauthorized_build_count_map,
)


def get_access_token_expiry(workspace: Workspace) -> datetime | None:
    if not workspace.access_token:
        return None

    try:
        return chatgpt_service.extract_access_token_expiry(workspace.access_token)
    except (PyJWTError, ValueError, TypeError):
        return None


def normalize_identity(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def get_current_user_role(workspace: Workspace, session: Session) -> str:
    if not workspace.access_token:
        return "user"

    token_user_id = None
    token_email = None

    try:
        token_user_id = normalize_identity(
            chatgpt_service.extract_user_id(workspace.access_token)
        )
    except (PyJWTError, ValueError, TypeError):
        token_user_id = None

    try:
        token_email = normalize_identity(
            chatgpt_service.extract_email(workspace.access_token)
        )
    except (PyJWTError, ValueError, TypeError):
        token_email = None

    members = (
        session.execute(select(Member).where(Member.org_id == workspace.org_id))
        .scalars()
        .all()
    )

    if token_user_id:
        for member in members:
            remote_id = normalize_identity(member.remote_id)
            if remote_id and remote_id == token_user_id:
                return member.role.lower()

    if token_email:
        for member in members:
            member_email = normalize_identity(member.email)
            if member_email and member_email == token_email:
                return member.role.lower()

    return "user"


def pending_invite_count(
    session: Session,
    org_id: str,
    pending_counts: dict[str, int] | None = None,
) -> int:
    if pending_counts is not None:
        return pending_counts.get(org_id, 0)
    return int(
        session.execute(
            select(func.count())
            .select_from(Invite)
            .where(Invite.org_id == org_id, Invite.status == "pending")
        ).scalar_one()
        or 0
    )


def build_pending_invite_count_map(
    session: Session,
    org_ids: list[str],
) -> dict[str, int]:
    if not org_ids:
        return {}

    rows = session.execute(
        select(Invite.org_id, func.count().label("pending_count"))
        .where(Invite.org_id.in_(org_ids), Invite.status == "pending")
        .group_by(Invite.org_id)
    ).all()
    return {str(org_id): int(pending_count or 0) for org_id, pending_count in rows}


def build_current_user_role_map(
    workspaces: list[Workspace],
    session: Session,
) -> dict[str, str]:
    org_ids = [workspace.org_id for workspace in workspaces]
    if not org_ids:
        return {}

    token_identity_by_org: dict[str, tuple[str | None, str | None]] = {}
    candidate_remote_ids: set[str] = set()
    candidate_emails: set[str] = set()

    for workspace in workspaces:
        token_user_id = None
        token_email = None
        if workspace.access_token:
            try:
                token_user_id = normalize_identity(
                    chatgpt_service.extract_user_id(workspace.access_token)
                )
            except (PyJWTError, ValueError, TypeError):
                token_user_id = None

            try:
                token_email = normalize_identity(
                    chatgpt_service.extract_email(workspace.access_token)
                )
            except (PyJWTError, ValueError, TypeError):
                token_email = None

        token_identity_by_org[workspace.org_id] = (token_user_id, token_email)
        if token_user_id:
            candidate_remote_ids.add(token_user_id)
        if token_email:
            candidate_emails.add(token_email)

    if not candidate_remote_ids and not candidate_emails:
        return {workspace.org_id: "user" for workspace in workspaces}

    member_filters = [Member.org_id.in_(org_ids)]
    identity_filters = []
    if candidate_remote_ids:
        identity_filters.append(func.lower(Member.remote_id).in_(candidate_remote_ids))
    if candidate_emails:
        identity_filters.append(func.lower(Member.email).in_(candidate_emails))
    if identity_filters:
        member_filters.append(
            identity_filters[0]
            if len(identity_filters) == 1
            else identity_filters[0] | identity_filters[1]
        )

    members = session.execute(select(Member).where(*member_filters)).scalars().all()

    members_by_org: dict[str, list[Member]] = {}
    for member in members:
        members_by_org.setdefault(member.org_id, []).append(member)

    role_map: dict[str, str] = {}
    for workspace in workspaces:
        token_user_id, token_email = token_identity_by_org[workspace.org_id]
        role = "user"
        for member in members_by_org.get(workspace.org_id, []):
            remote_id = normalize_identity(member.remote_id)
            if token_user_id and remote_id and remote_id == token_user_id:
                role = member.role.lower()
                break
        else:
            for member in members_by_org.get(workspace.org_id, []):
                member_email = normalize_identity(member.email)
                if token_email and member_email and member_email == token_email:
                    role = member.role.lower()
                    break
        role_map[workspace.org_id] = role

    return role_map


def workspace_to_dict(
    workspace: Workspace,
    session: Session,
    *,
    current_user_role: str | None = None,
    pending_invites: int | None = None,
    unauthorized_active_count: int | None = None,
) -> dict[str, Any]:
    resolved_current_user_role = current_user_role or get_current_user_role(
        workspace, session
    )
    resolved_pending_invites = (
        pending_invites
        if pending_invites is not None
        else pending_invite_count(session, workspace.org_id)
    )
    resolved_unauthorized_count = (
        unauthorized_active_count
        if unauthorized_active_count is not None
        else get_unauthorized_active_count(session, workspace.org_id)
    )
    now = utc_now()
    hot_until = coerce_utc(workspace.hot_until)
    is_hot = bool(hot_until and hot_until > now)
    return {
        "id": workspace.id,
        "org_id": workspace.org_id,
        "account_id": workspace.account_id,
        "name": workspace.name,
        "status": workspace.status,
        "member_count": workspace.member_count,
        "member_limit": workspace.member_limit,
        "pending_invites": resolved_pending_invites,
        "unauthorized_member_mode": workspace.unauthorized_member_mode,
        "unauthorized_active_count": resolved_unauthorized_count,
        "unauthorized_last_detected_at": serialize_datetime(
            workspace.unauthorized_last_detected_at
        ),
        "expires_at": serialize_datetime(workspace.expires_at),
        "access_token_expires_at": serialize_datetime(
            get_access_token_expiry(workspace)
        ),
        "last_sync": serialize_datetime(workspace.last_sync),
        "created_at": serialize_datetime(workspace.created_at),
        "current_user_role": resolved_current_user_role,
        "can_manage_members": resolved_current_user_role in ("owner", "admin"),
        "sync_error": workspace.sync_error,
        "sync_started_at": serialize_datetime(workspace.sync_started_at),
        "sync_finished_at": serialize_datetime(workspace.sync_finished_at),
        "next_sync_at": serialize_datetime(workspace.next_sync_at),
        "hot_until": serialize_datetime(workspace.hot_until),
        "last_activity_at": serialize_datetime(workspace.last_activity_at),
        "sync_reason": workspace.sync_reason,
        "sync_priority": workspace.sync_priority,
        "is_hot": is_hot,
        "last_token_refresh_at": serialize_datetime(workspace.last_token_refresh_at),
        "last_token_refresh_error": workspace.last_token_refresh_error,
        "token_refresh_fail_count": int(workspace.token_refresh_fail_count or 0),
        "token_refresh_blocked": bool(workspace.token_refresh_blocked),
    }


def build_workspace_list_payload(
    workspaces: list[Workspace],
    session: Session,
) -> list[dict[str, Any]]:
    org_ids = [workspace.org_id for workspace in workspaces]
    pending_counts = build_pending_invite_count_map(session, org_ids)
    role_map = build_current_user_role_map(workspaces, session)
    unauthorized_counts = unauthorized_build_count_map(session, org_ids)
    return [
        workspace_to_dict(
            workspace,
            session,
            current_user_role=role_map.get(workspace.org_id, "user"),
            pending_invites=pending_counts.get(workspace.org_id, 0),
            unauthorized_active_count=unauthorized_counts.get(workspace.org_id, 0),
        )
        for workspace in workspaces
    ]
