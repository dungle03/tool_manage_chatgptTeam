import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from jwt import PyJWTError
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Invite, Member, UnauthorizedFinding, Workspace
from app.services.chatgpt import chatgpt_service
from app.services.events import workspace_event_broker
from app.services.token_refresher import (
    TokenRefreshError,
    get_workspace_token_refresh_lock,
    is_workspace_token_refresh_in_progress,
    mark_workspace_refresh_failure,
    mark_workspace_refresh_success,
    run_token_refresher_for_workspace,
    select_due_token_refresh_workspace_ids,
    verify_refreshed_token_for_workspace,
)

logger = logging.getLogger(__name__)

_SYNC_LOCKS: dict[str, asyncio.Lock] = {}
_BACKGROUND_TASK: asyncio.Task[None] | None = None
_STOP_EVENT: asyncio.Event | None = None

SYNC_LOOP_INTERVAL_SECONDS = int(os.getenv("SYNC_LOOP_INTERVAL_SECONDS", "5"))
SYNC_STALE_MINUTES = int(os.getenv("SYNC_STALE_MINUTES", "5"))
SYNC_PENDING_INVITE_SECONDS = int(os.getenv("SYNC_PENDING_INVITE_SECONDS", "15"))
SYNC_BASELINE_MINUTES = int(os.getenv("SYNC_BASELINE_MINUTES", str(SYNC_STALE_MINUTES)))
SYNC_HOT_WINDOW_SECONDS = int(os.getenv("SYNC_HOT_WINDOW_SECONDS", "180"))
SYNC_MAX_PARALLEL_WORKSPACES = max(
    1, int(os.getenv("SYNC_MAX_PARALLEL_WORKSPACES", "2"))
)
TOKEN_AUTO_REFRESH_MAX_PARALLEL = max(
    1, int(os.getenv("TOKEN_AUTO_REFRESH_MAX_PARALLEL", "3"))
)
TOKEN_AUTO_REFRESH_BATCH_DELAY_SECONDS = max(
    0, int(os.getenv("TOKEN_AUTO_REFRESH_BATCH_DELAY_SECONDS", "60"))
)


def _parse_step_list(raw_value: str, fallback: list[int]) -> list[int]:
    values: list[int] = []
    for item in raw_value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            parsed = int(item)
        except ValueError:
            continue
        if parsed > 0:
            values.append(parsed)
    return values or fallback


SYNC_FOLLOWUP_STEPS = _parse_step_list(
    os.getenv("SYNC_FOLLOWUP_STEPS", "5,15,30,60"),
    [5, 15, 30, 60],
)
SYNC_ERROR_RETRY_STEPS = _parse_step_list(
    os.getenv("SYNC_ERROR_RETRY_STEPS", "10,30,60"),
    [10, 30, 60],
)


def _get_workspace_lock(org_id: str) -> asyncio.Lock:
    lock = _SYNC_LOCKS.get(org_id)
    if lock is None:
        lock = asyncio.Lock()
        _SYNC_LOCKS[org_id] = lock
    return lock


def is_workspace_sync_in_progress(org_id: str) -> bool:
    return _get_workspace_lock(org_id).locked()


def build_refresh_hint(
    *,
    scope: str,
    reason: str,
    org_id: str | None = None,
    include_details: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "scope": scope,
        "reason": reason,
        "include_details": include_details,
    }
    if org_id is not None:
        payload["org_id"] = org_id
    return payload


def serialize_invite_row(invite: Invite) -> dict[str, Any]:
    return {
        "id": invite.id,
        "org_id": invite.org_id,
        "email": invite.email,
        "invite_id": invite.invite_id,
        "status": invite.status,
        "created_by_tool": bool(invite.created_by_tool),
        "created_at": serialize_datetime(invite.created_at),
    }


def serialize_member_row(member: Member) -> dict[str, Any]:
    return {
        "id": member.id,
        "remote_id": member.remote_id,
        "name": member.name,
        "email": member.email,
        "role": member.role,
        "status": member.status,
        "invite_date": serialize_datetime(member.invite_date),
        "created_at": serialize_datetime(member.created_at),
        "picture": member.picture,
    }


def serialize_unauthorized_finding_row(finding: UnauthorizedFinding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "org_id": finding.org_id,
        "remote_id": finding.remote_id,
        "email": finding.email,
        "name": finding.name,
        "role": finding.role,
        "status": finding.status,
        "detection_reason": finding.detection_reason,
        "action_reason": finding.action_reason,
        "first_seen_at": serialize_datetime(finding.first_seen_at),
        "last_seen_at": serialize_datetime(finding.last_seen_at),
        "resolved_at": serialize_datetime(finding.resolved_at),
        "created_at": serialize_datetime(finding.created_at),
        "updated_at": serialize_datetime(finding.updated_at),
    }


def _active_unauthorized_statuses() -> tuple[str, ...]:
    return ("detected", "kick_failed")


def _build_unauthorized_count_map(
    session: Session,
    org_ids: list[str],
) -> dict[str, int]:
    if not org_ids:
        return {}

    rows = session.execute(
        select(UnauthorizedFinding.org_id, func.count().label("active_count"))
        .where(
            UnauthorizedFinding.org_id.in_(org_ids),
            UnauthorizedFinding.status.in_(_active_unauthorized_statuses()),
        )
        .group_by(UnauthorizedFinding.org_id)
    ).all()
    return {str(org_id): int(active_count or 0) for org_id, active_count in rows}


def _active_unauthorized_count(session: Session, org_id: str) -> int:
    return int(
        session.execute(
            select(func.count())
            .select_from(UnauthorizedFinding)
            .where(
                UnauthorizedFinding.org_id == org_id,
                UnauthorizedFinding.status.in_(_active_unauthorized_statuses()),
            )
        ).scalar_one()
        or 0
    )


def _normalize_remote_member(item: dict[str, Any]) -> dict[str, Any]:
    created_raw = (
        item.get("created_time") or item.get("created_at") or item.get("created")
    )
    return {
        "remote_id": str(item.get("id") or "") or None,
        "email": item.get("email") or "",
        "name": item.get("name") or "",
        "role": normalize_member_role(item),
        "status": item.get("status") or "active",
        "created_at": parse_datetime(created_raw),
        "picture": item.get("picture"),
    }


def _upsert_unauthorized_finding(
    session: Session,
    *,
    workspace: Workspace,
    member: dict[str, Any],
    detected_at: datetime,
) -> UnauthorizedFinding:
    normalized_email = normalize_identity(member.get("email")) or ""
    remote_id = member.get("remote_id")

    existing = None
    if remote_id:
        existing = session.execute(
            select(UnauthorizedFinding).where(
                UnauthorizedFinding.org_id == workspace.org_id,
                UnauthorizedFinding.remote_id == remote_id,
            )
        ).scalar_one_or_none()
    if existing is None and normalized_email:
        existing = session.execute(
            select(UnauthorizedFinding).where(
                UnauthorizedFinding.org_id == workspace.org_id,
                func.lower(UnauthorizedFinding.email) == normalized_email,
            )
        ).scalar_one_or_none()

    if existing is None:
        existing = UnauthorizedFinding(
            org_id=workspace.org_id,
            remote_id=remote_id,
            email=member.get("email") or "",
            name=member.get("name") or "",
            role=member.get("role") or "user",
            status="detected",
            detection_reason="missing_from_local_whitelist",
            first_seen_at=detected_at,
            last_seen_at=detected_at,
            created_at=detected_at,
            updated_at=detected_at,
        )
        session.add(existing)
        session.flush()
        return existing

    existing.remote_id = remote_id or existing.remote_id
    existing.email = member.get("email") or existing.email
    existing.name = member.get("name") or existing.name
    existing.role = member.get("role") or existing.role
    existing.last_seen_at = detected_at
    existing.updated_at = detected_at
    existing.resolved_at = None
    if existing.status not in {"trusted", "kicked"}:
        existing.status = "detected"
        existing.action_reason = None
    return existing


def _mark_missing_findings_resolved(
    session: Session,
    *,
    workspace: Workspace,
    active_remote_keys: set[tuple[str | None, str | None]],
    resolved_at: datetime,
) -> None:
    findings = (
        session.execute(
            select(UnauthorizedFinding).where(
                UnauthorizedFinding.org_id == workspace.org_id
            )
        )
        .scalars()
        .all()
    )
    updated = False
    for finding in findings:
        finding_key = (
            normalize_identity(finding.remote_id),
            normalize_identity(finding.email),
        )
        if finding_key in active_remote_keys:
            continue
        if finding.status in _active_unauthorized_statuses():
            previous_status = finding.status
            finding.resolved_at = resolved_at
            finding.updated_at = resolved_at
            finding.status = "trusted"
            if previous_status == "detected":
                finding.action_reason = (
                    finding.action_reason or "member_no_longer_present"
                )
            else:
                finding.action_reason = (
                    finding.action_reason
                    or "member_no_longer_present_after_kick_failure"
                )
            updated = True

    if updated:
        session.flush()


def _auto_resolve_stale_finding(
    session: Session,
    *,
    workspace: Workspace,
    remote_id: str | None,
    email: str | None,
    resolved_at: datetime,
) -> None:
    """Resolve any active finding for a member who is now whitelisted.

    This handles the case where an invitee was flagged as unauthorized
    (e.g. they accepted an invite after auto-kick was enabled) but is
    now a legitimate member in the whitelist.
    """
    if not remote_id and not email:
        return

    filters = [UnauthorizedFinding.org_id == workspace.org_id]
    identity_clauses = []
    if remote_id:
        identity_clauses.append(func.lower(UnauthorizedFinding.remote_id) == remote_id)
    if email:
        identity_clauses.append(func.lower(UnauthorizedFinding.email) == email)
    if len(identity_clauses) == 1:
        filters.append(identity_clauses[0])
    else:
        filters.append(identity_clauses[0] | identity_clauses[1])

    filters.append(UnauthorizedFinding.status.in_(_active_unauthorized_statuses()))

    stale_findings = (
        session.execute(select(UnauthorizedFinding).where(*filters)).scalars().all()
    )

    for finding in stale_findings:
        finding.status = "trusted"
        finding.action_reason = "whitelisted_member_auto_resolved"
        finding.resolved_at = resolved_at
        finding.updated_at = resolved_at

    if stale_findings:
        session.flush()


def build_action_response(
    *,
    action: str,
    workspace: Workspace | None = None,
    session: Session | None = None,
    updated_record: dict[str, Any] | None = None,
    updated_summary: dict[str, Any] | None = None,
    refresh_hint: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"ok": True, "action": action}

    if updated_summary is None and workspace is not None and session is not None:
        updated_summary = workspace_to_dict(workspace, session)

    if updated_record is not None:
        payload["updated_record"] = updated_record
    if updated_summary is not None:
        payload["updated_summary"] = updated_summary
    if refresh_hint is not None:
        payload["refresh_hint"] = refresh_hint
    if extra:
        payload.update(extra)
    return payload


def _persist_sync_failure(
    session: Session,
    *,
    workspace_id: int | None,
    error_message: str,
) -> Workspace | None:
    session.rollback()
    if workspace_id is None:
        return None

    managed_workspace = session.get(Workspace, workspace_id)
    if managed_workspace is None:
        return None

    managed_workspace.status = "error"
    managed_workspace.sync_error = error_message
    managed_workspace.sync_finished_at = utc_now()
    _schedule_retry_after_failure(session, managed_workspace)
    session.commit()
    return managed_workspace


def build_sync_in_progress_payload(
    workspace: Workspace, session: Session
) -> dict[str, Any]:
    return {
        "ok": True,
        "action": "sync_workspace",
        "already_in_progress": True,
        "members_synced": 0,
        "invites_synced": 0,
        "last_sync": serialize_datetime(workspace.last_sync),
        "updated_summary": workspace_to_dict(workspace, session),
        "refresh_hint": build_refresh_hint(
            scope="workspace_detail",
            org_id=workspace.org_id,
            reason="sync_already_in_progress",
            include_details=True,
        ),
    }


def parse_datetime(value: str | int | float | datetime | None) -> datetime | None:
    if value is None:
        return None

    parsed: datetime | None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        epoch = float(value)
        if abs(epoch) >= 10_000_000_000:
            epoch /= 1000
        try:
            parsed = datetime.fromtimestamp(epoch, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str):
        if not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_access_token_expiry(workspace: Workspace) -> datetime | None:
    if not workspace.access_token:
        return None

    try:
        return chatgpt_service.extract_access_token_expiry(workspace.access_token)
    except (PyJWTError, ValueError, TypeError):
        return None


def coerce_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _step_index_from_reason(reason: str | None) -> int:
    if not reason or not reason.startswith("followup:"):
        return -1
    try:
        return int(reason.split(":", 1)[1])
    except ValueError:
        return -1


def _priority_for_workspace(
    workspace: Workspace, pending_invites: int, now: datetime
) -> int:
    hot_until = coerce_utc(workspace.hot_until)
    if workspace.status == "error":
        return 80
    if pending_invites > 0:
        return 100
    if hot_until and hot_until > now:
        return 90
    return 10


def _publish_schedule_event(workspace: Workspace, pending_invites: int) -> None:
    hot_until = coerce_utc(workspace.hot_until)
    workspace_event_broker.publish(
        "workspace_scheduled",
        org_id=workspace.org_id,
        reason=workspace.sync_reason,
        next_sync_at=serialize_datetime(workspace.next_sync_at),
        hot_until=serialize_datetime(workspace.hot_until),
        is_hot=bool(hot_until is not None and hot_until > utc_now()),
        pending_invites=pending_invites,
        priority=workspace.sync_priority,
    )


def schedule_followup_sync(
    session: Session,
    workspace: Workspace,
    *,
    reason: str,
    delay_seconds: int | None = None,
    hot_window_seconds: int | None = None,
    publish_event: bool = True,
) -> None:
    now = utc_now()
    pending_invites = _pending_invite_count(session, workspace.org_id)
    effective_hot_window = (
        hot_window_seconds
        if hot_window_seconds is not None
        else SYNC_HOT_WINDOW_SECONDS
    )
    hot_until = now + timedelta(seconds=max(0, effective_hot_window))
    effective_delay = (
        delay_seconds if delay_seconds is not None else SYNC_FOLLOWUP_STEPS[0]
    )
    next_sync_at = now + timedelta(seconds=max(0, effective_delay))

    current_hot_until = coerce_utc(workspace.hot_until)
    current_next_sync_at = coerce_utc(workspace.next_sync_at)
    workspace.last_activity_at = now
    workspace.hot_until = (
        max(current_hot_until, hot_until) if current_hot_until else hot_until
    )
    workspace.next_sync_at = (
        min(current_next_sync_at, next_sync_at)
        if current_next_sync_at is not None
        else next_sync_at
    )
    workspace.sync_reason = reason
    workspace.sync_priority = _priority_for_workspace(workspace, pending_invites, now)

    if publish_event:
        _publish_schedule_event(workspace, pending_invites)


def _set_baseline_schedule(
    workspace: Workspace,
    *,
    now: datetime,
    pending_invites: int,
) -> None:
    workspace.hot_until = None
    workspace.next_sync_at = now + timedelta(minutes=SYNC_BASELINE_MINUTES)
    workspace.sync_reason = "baseline_refresh"
    workspace.sync_priority = _priority_for_workspace(workspace, pending_invites, now)


def _schedule_next_sync_after_success(
    session: Session,
    workspace: Workspace,
    *,
    pending_invites: int,
) -> None:
    last_sync = coerce_utc(workspace.last_sync) or utc_now()

    if pending_invites > 0:
        schedule_followup_sync(
            session,
            workspace,
            reason="pending_invite_watch",
            delay_seconds=SYNC_PENDING_INVITE_SECONDS,
            publish_event=False,
        )
        return

    hot_until = coerce_utc(workspace.hot_until)
    current_step_index = _step_index_from_reason(workspace.sync_reason)
    has_active_hot_window = bool(hot_until and hot_until > last_sync)

    if has_active_hot_window:
        next_step_index = current_step_index + 1
        if 0 <= next_step_index < len(SYNC_FOLLOWUP_STEPS):
            schedule_followup_sync(
                session,
                workspace,
                reason=f"followup:{next_step_index}",
                delay_seconds=SYNC_FOLLOWUP_STEPS[next_step_index],
                publish_event=False,
            )
            return

    _set_baseline_schedule(
        workspace,
        now=last_sync,
        pending_invites=pending_invites,
    )


def _schedule_retry_after_failure(
    session: Session,
    workspace: Workspace,
) -> None:
    retry_delay = SYNC_ERROR_RETRY_STEPS[0]
    schedule_followup_sync(
        session,
        workspace,
        reason="retry_after_error",
        delay_seconds=retry_delay,
        publish_event=False,
    )


def normalize_member_role(item: dict[str, Any]) -> str:
    raw_values = [
        item.get("role"),
        item.get("role_name"),
        item.get("account_type"),
        item.get("membership_role"),
        item.get("workspace_role"),
        item.get("type"),
    ]

    normalized_values = [
        str(value).strip().lower().replace("_", "-")
        for value in raw_values
        if value not in (None, "")
    ]

    owner_tokens = {
        "owner",
        "primary-owner",
        "primary-owner-user",
        "primary",
        "plan-owner",
        "plan-owner-user",
        "workspace-owner",
        "team-owner",
    }
    admin_tokens = {
        "admin",
        "workspace-admin",
        "team-admin",
        "operator",
        "manager",
    }
    user_tokens = {
        "member",
        "user",
        "standard-user",
        "standard-member",
        "workspace-user",
        "team-user",
        "regular-user",
    }

    for value in normalized_values:
        if value in owner_tokens or "owner" in value:
            return "owner"
        if value in admin_tokens or value.endswith("-admin") or "admin" in value:
            return "admin"
        if value in user_tokens or "user" in value or "member" in value:
            return "user"

    return "user"


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


async def resolve_access_token(workspace: Workspace) -> str:
    if workspace.access_token:
        return workspace.access_token

    raise HTTPException(status_code=400, detail="workspace missing access token")


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
        else _pending_invite_count(session, workspace.org_id)
    )
    resolved_unauthorized_count = (
        unauthorized_active_count
        if unauthorized_active_count is not None
        else _active_unauthorized_count(session, workspace.org_id)
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


def _pending_invite_count(
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


def _build_pending_invite_count_map(
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


def _build_current_user_role_map(
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
        else _pending_invite_count(session, workspace.org_id)
    )
    resolved_unauthorized_count = (
        unauthorized_active_count
        if unauthorized_active_count is not None
        else _active_unauthorized_count(session, workspace.org_id)
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
    pending_counts = _build_pending_invite_count_map(session, org_ids)
    role_map = _build_current_user_role_map(workspaces, session)
    unauthorized_counts = _build_unauthorized_count_map(session, org_ids)
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


async def sync_workspace_data(
    session: Session,
    workspace: Workspace,
    *,
    trigger: str = "manual",
    publish_events: bool = True,
) -> dict[str, Any]:
    lock = _get_workspace_lock(workspace.org_id)
    if lock.locked():
        raise HTTPException(
            status_code=409, detail="workspace sync already in progress"
        )

    async with lock:
        workspace_id = workspace.id
        workspace_org_id = workspace.org_id
        now = utc_now()
        workspace.status = "syncing"
        workspace.sync_error = None
        workspace.sync_started_at = now
        workspace.next_sync_at = None
        workspace.sync_priority = _priority_for_workspace(
            workspace, _pending_invite_count(session, workspace_org_id), now
        )
        session.commit()

        if publish_events:
            workspace_event_broker.publish(
                "sync_started",
                org_id=workspace_org_id,
                trigger=trigger,
            )

        account_id = workspace.account_id or workspace_org_id

        try:
            access_token = await resolve_access_token(workspace)
            remote_members, remote_invites = await asyncio.gather(
                chatgpt_service.get_members(access_token, account_id),
                chatgpt_service.get_invites(access_token, account_id),
            )

            existing_local_members = (
                session.execute(select(Member).where(Member.org_id == workspace.org_id))
                .scalars()
                .all()
            )
            whitelisted_remote_ids = {
                normalize_identity(member.remote_id)
                for member in existing_local_members
                if normalize_identity(member.remote_id)
            }
            whitelisted_emails = {
                normalize_identity(member.email)
                for member in existing_local_members
                if normalize_identity(member.email)
            }

            # Only whitelist pending invites that were explicitly created or
            # confirmed via this tool. Remote-only pending invites can be
            # initiated by other members and must not grant authorization.
            pending_invites_rows = (
                session.execute(
                    select(Invite).where(
                        Invite.org_id == workspace.org_id,
                        Invite.status == "pending",
                        Invite.created_by_tool.is_(True),
                    )
                )
                .scalars()
                .all()
            )
            for inv in pending_invites_rows:
                inv_email = normalize_identity(inv.email)
                if inv_email:
                    whitelisted_emails.add(inv_email)

            normalized_remote_members = [
                _normalize_remote_member(item) for item in remote_members
            ]
            unauthorized_members: list[dict[str, Any]] = []
            active_remote_keys: set[tuple[str | None, str | None]] = set()
            auto_kicked_remote_ids: set[str] = set()
            detected_at = utc_now()

            for member in normalized_remote_members:
                remote_id_key = normalize_identity(member.get("remote_id"))
                email_key = normalize_identity(member.get("email"))
                active_remote_keys.add((remote_id_key, email_key))
                is_whitelisted = False
                if remote_id_key and remote_id_key in whitelisted_remote_ids:
                    is_whitelisted = True
                elif email_key and email_key in whitelisted_emails:
                    is_whitelisted = True

                if not is_whitelisted:
                    unauthorized_members.append(member)
                    finding = _upsert_unauthorized_finding(
                        session,
                        workspace=workspace,
                        member=member,
                        detected_at=detected_at,
                    )
                    if workspace.unauthorized_member_mode == "auto_kick":
                        remote_id = member.get("remote_id")
                        if remote_id and member.get("role") != "owner":
                            try:
                                await chatgpt_service.delete_member(
                                    access_token,
                                    account_id,
                                    remote_id,
                                )
                                finding.status = "kicked"
                                finding.action_reason = "auto_kick_sync_enforcement"
                                finding.resolved_at = detected_at
                                normalized_remote_id = normalize_identity(remote_id)
                                if normalized_remote_id:
                                    auto_kicked_remote_ids.add(normalized_remote_id)
                            except Exception as exc:
                                finding.status = "kick_failed"
                                finding.action_reason = str(exc)
                                finding.resolved_at = None
                        else:
                            finding.status = "kick_failed"
                            finding.action_reason = "remote_id_missing_or_owner"
                            finding.resolved_at = None
                        finding.updated_at = detected_at
                else:
                    # Member is legitimate — auto-resolve any stale finding
                    # (e.g. invitee accepted after auto-kick was enabled)
                    _auto_resolve_stale_finding(
                        session,
                        workspace=workspace,
                        remote_id=remote_id_key,
                        email=email_key,
                        resolved_at=detected_at,
                    )

            synced_members_for_cache = [
                member
                for member in normalized_remote_members
                if normalize_identity(member.get("remote_id"))
                not in auto_kicked_remote_ids
            ]

            if unauthorized_members:
                workspace.unauthorized_last_detected_at = detected_at

            _mark_missing_findings_resolved(
                session,
                workspace=workspace,
                active_remote_keys=active_remote_keys,
                resolved_at=detected_at,
            )

            session.query(Member).where(Member.org_id == workspace.org_id).delete()

            existing_invites = (
                session.execute(select(Invite).where(Invite.org_id == workspace.org_id))
                .scalars()
                .all()
            )
            invites_by_id = {
                invite.invite_id: invite
                for invite in existing_invites
                if invite.invite_id
            }
            invites_by_email = {
                invite.email.strip().lower(): invite
                for invite in existing_invites
                if invite.email
            }
            seen_invite_row_ids: set[int] = set()

            synced_member_emails: set[str] = set()

            for member in synced_members_for_cache:
                normalized_member_email = (member.get("email") or "").strip().lower()
                if normalized_member_email:
                    synced_member_emails.add(normalized_member_email)

                session.add(
                    Member(
                        org_id=workspace.org_id,
                        remote_id=member.get("remote_id"),
                        email=member.get("email") or "",
                        name=member.get("name") or "",
                        role=member.get("role") or "user",
                        status=member.get("status") or "active",
                        invite_date=member.get("created_at"),
                        created_at=member.get("created_at"),
                        picture=member.get("picture"),
                    )
                )

            for index, item in enumerate(remote_invites, start=1):
                invite_id = str(
                    item.get("id")
                    or item.get("invite_id")
                    or f"inv_{workspace.org_id}_{index}"
                )
                email = item.get("email") or item.get("email_address") or ""
                normalized_email = email.strip().lower()
                created_at = parse_datetime(
                    item.get("created_at") or item.get("created")
                )
                existing_invite = invites_by_id.get(invite_id)
                if existing_invite is None and normalized_email:
                    existing_invite = invites_by_email.get(normalized_email)

                if existing_invite:
                    existing_invite.email = email
                    existing_invite.invite_id = invite_id
                    existing_invite.status = item.get("status") or "pending"
                    existing_invite.created_at = (
                        created_at or existing_invite.created_at
                    )
                    seen_invite_row_ids.add(existing_invite.id)
                else:
                    invite = Invite(
                        org_id=workspace.org_id,
                        email=email,
                        invite_id=invite_id,
                        status=item.get("status") or "pending",
                        created_by_tool=False,
                        created_at=created_at or datetime.now(timezone.utc),
                    )
                    session.add(invite)
                    session.flush()
                    seen_invite_row_ids.add(invite.id)

            for existing_invite in existing_invites:
                normalized_existing_email = (
                    (existing_invite.email or "").strip().lower()
                )
                if (
                    normalized_existing_email
                    and normalized_existing_email in synced_member_emails
                ):
                    session.delete(existing_invite)
                    continue
                if existing_invite.id in seen_invite_row_ids:
                    continue
                if existing_invite.status == "pending":
                    continue
                session.delete(existing_invite)

            workspace.member_count = len(synced_members_for_cache)
            workspace.last_sync = utc_now()
            workspace.sync_finished_at = workspace.last_sync
            workspace.status = "live"
            workspace.sync_error = None
            pending_invites = _pending_invite_count(session, workspace.org_id)
            unauthorized_active_count = _active_unauthorized_count(
                session, workspace.org_id
            )
            unauthorized_kicked = len(
                [
                    member
                    for member in unauthorized_members
                    if workspace.unauthorized_member_mode == "auto_kick"
                ]
            ) - int(
                session.execute(
                    select(func.count())
                    .select_from(UnauthorizedFinding)
                    .where(
                        UnauthorizedFinding.org_id == workspace.org_id,
                        UnauthorizedFinding.last_seen_at == detected_at,
                        UnauthorizedFinding.status == "kick_failed",
                    )
                ).scalar_one()
                or 0
            )
            unauthorized_kicked = max(unauthorized_kicked, 0)
            _schedule_next_sync_after_success(
                session,
                workspace,
                pending_invites=pending_invites,
            )

            session.commit()

            payload = {
                "ok": True,
                "members_synced": len(remote_members),
                "invites_synced": len(remote_invites),
                "last_sync": serialize_datetime(workspace.last_sync),
                "unauthorized_detected": len(unauthorized_members),
                "unauthorized_kicked": unauthorized_kicked,
                "updated_summary": workspace_to_dict(
                    workspace,
                    session,
                    pending_invites=pending_invites,
                    unauthorized_active_count=unauthorized_active_count,
                ),
                "refresh_hint": build_refresh_hint(
                    scope="workspace_detail",
                    org_id=workspace.org_id,
                    reason="workspace_synced",
                    include_details=True,
                ),
            }
            if publish_events:
                workspace_event_broker.publish(
                    "workspace_updated",
                    org_id=workspace.org_id,
                    trigger=trigger,
                    summary={
                        "member_count": workspace.member_count,
                        "pending_invites": pending_invites,
                        "unauthorized_active_count": unauthorized_active_count,
                        "status": workspace.status,
                        "last_sync": payload["last_sync"],
                    },
                )
                _publish_schedule_event(workspace, pending_invites)
            return payload
        except HTTPException as exc:
            failed_workspace = _persist_sync_failure(
                session,
                workspace_id=workspace_id,
                error_message=(
                    exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                ),
            )
            if publish_events:
                workspace_event_broker.publish(
                    "sync_failed",
                    org_id=workspace_org_id,
                    trigger=trigger,
                    error={
                        "message": (
                            failed_workspace.sync_error
                            if failed_workspace is not None
                            else (
                                exc.detail
                                if isinstance(exc.detail, str)
                                else str(exc.detail)
                            )
                        )
                    },
                )
                if failed_workspace is not None:
                    _publish_schedule_event(
                        failed_workspace,
                        _pending_invite_count(session, workspace_org_id),
                    )
            raise
        except Exception as exc:
            failed_workspace = _persist_sync_failure(
                session,
                workspace_id=workspace_id,
                error_message=str(exc),
            )
            if publish_events:
                workspace_event_broker.publish(
                    "sync_failed",
                    org_id=workspace_org_id,
                    trigger=trigger,
                    error={
                        "message": (
                            failed_workspace.sync_error
                            if failed_workspace is not None
                            else str(exc)
                        )
                    },
                )
                if failed_workspace is not None:
                    _publish_schedule_event(
                        failed_workspace,
                        _pending_invite_count(session, workspace_org_id),
                    )
            raise HTTPException(
                status_code=502,
                detail=f"workspace sync failed: {exc}",
            ) from exc


def list_stale_workspace_ids(session: Session) -> list[str]:
    return [
        workspace.org_id for workspace in pick_due_workspaces(session, limit=10_000)
    ]


def pick_due_workspaces(session: Session, *, limit: int) -> list[Workspace]:
    now = utc_now()
    baseline_cutoff = now - timedelta(minutes=SYNC_BASELINE_MINUTES)
    pending_cutoff = now - timedelta(seconds=SYNC_PENDING_INVITE_SECONDS)
    pending_org_ids = (
        session.execute(
            select(Invite.org_id).where(Invite.status == "pending").distinct()
        )
        .scalars()
        .all()
    )

    candidate_filter = (
        (Workspace.next_sync_at <= now)
        | Workspace.last_sync.is_(None)
        | (Workspace.last_sync <= baseline_cutoff)
        | (Workspace.status == "error")
    )
    if pending_org_ids:
        candidate_filter = candidate_filter | Workspace.org_id.in_(pending_org_ids)

    workspaces = (
        session.execute(
            select(Workspace).where(candidate_filter).order_by(Workspace.org_id)
        )
        .scalars()
        .all()
    )
    pending_counts = _build_pending_invite_count_map(
        session, [workspace.org_id for workspace in workspaces]
    )
    due_workspaces: list[Workspace] = []

    for workspace in workspaces:
        if _get_workspace_lock(workspace.org_id).locked():
            continue

        pending_invites = pending_counts.get(workspace.org_id, 0)
        next_sync_at = coerce_utc(workspace.next_sync_at)
        last_sync = coerce_utc(workspace.last_sync)

        if next_sync_at and next_sync_at <= now:
            workspace.sync_priority = _priority_for_workspace(
                workspace, pending_invites, now
            )
            due_workspaces.append(workspace)
            continue

        if workspace.last_sync is None:
            workspace.sync_reason = workspace.sync_reason or "baseline_refresh"
            workspace.sync_priority = _priority_for_workspace(
                workspace, pending_invites, now
            )
            due_workspaces.append(workspace)
            continue

        if pending_invites > 0 and last_sync and last_sync <= pending_cutoff:
            workspace.sync_reason = "pending_invite_watch"
            workspace.sync_priority = _priority_for_workspace(
                workspace, pending_invites, now
            )
            due_workspaces.append(workspace)
            continue

        if last_sync and last_sync <= baseline_cutoff:
            workspace.sync_reason = workspace.sync_reason or "baseline_refresh"
            workspace.sync_priority = _priority_for_workspace(
                workspace, pending_invites, now
            )
            due_workspaces.append(workspace)

    due_workspaces.sort(
        key=lambda workspace: (
            -int(workspace.sync_priority or 0),
            coerce_utc(workspace.next_sync_at)
            or datetime.min.replace(tzinfo=timezone.utc),
            coerce_utc(workspace.last_activity_at)
            or datetime.min.replace(tzinfo=timezone.utc),
            workspace.org_id,
        )
    )
    return due_workspaces[:limit]


async def run_sync_cycle(session_factory: Any) -> None:
    session = session_factory()
    try:
        due_workspaces = pick_due_workspaces(
            session, limit=SYNC_MAX_PARALLEL_WORKSPACES
        )
        due_ids = [workspace.org_id for workspace in due_workspaces]
    finally:
        session.close()

    async def sync_one(org_id: str) -> None:
        session = session_factory()
        try:
            workspace = session.execute(
                select(Workspace).where(Workspace.org_id == org_id)
            ).scalar_one_or_none()
            if workspace is None:
                return
            try:
                await sync_workspace_data(
                    session, workspace, trigger="auto", publish_events=True
                )
            except HTTPException:
                return
        finally:
            session.close()

    await asyncio.gather(*(sync_one(org_id) for org_id in due_ids))


async def run_token_refresh_cycle(session_factory: Any) -> None:
    session = session_factory()
    try:
        due_ids = select_due_token_refresh_workspace_ids(session)
    finally:
        session.close()

    if not due_ids:
        return

    async def refresh_one(org_id: str) -> None:
        refresh_lock = get_workspace_token_refresh_lock(org_id)
        if refresh_lock.locked() or is_workspace_sync_in_progress(org_id):
            return

        async with refresh_lock:
            session = session_factory()
            try:
                workspace = session.execute(
                    select(Workspace).where(Workspace.org_id == org_id)
                ).scalar_one_or_none()
                if workspace is None:
                    return
                try:
                    refresh_result = await run_token_refresher_for_workspace(
                        session,
                        workspace,
                        mode="auto",
                    )
                    verified_result = await verify_refreshed_token_for_workspace(
                        workspace, refresh_result
                    )
                    mark_workspace_refresh_success(workspace, verified_result)
                    session.commit()
                    session.refresh(workspace)
                except TokenRefreshError as exc:
                    session.rollback()
                    managed_workspace = session.execute(
                        select(Workspace).where(Workspace.org_id == org_id)
                    ).scalar_one_or_none()
                    if managed_workspace is not None:
                        mark_workspace_refresh_failure(
                            managed_workspace,
                            exc.message,
                            mode="auto",
                        )
                        session.commit()
                    logger.warning(
                        "Auto token refresh failed for workspace %s: %s",
                        org_id,
                        exc.message,
                    )
                    return

                try:
                    await sync_workspace_data(
                        session,
                        workspace,
                        trigger="auto",
                        publish_events=True,
                    )
                except HTTPException as exc:
                    logger.warning(
                        "Auto token refresh sync follow-up failed for workspace %s: %s",
                        org_id,
                        exc.detail,
                    )
            finally:
                session.close()

    for batch_start in range(0, len(due_ids), TOKEN_AUTO_REFRESH_MAX_PARALLEL):
        batch_ids = due_ids[batch_start : batch_start + TOKEN_AUTO_REFRESH_MAX_PARALLEL]
        await asyncio.gather(*(refresh_one(org_id) for org_id in batch_ids))
        if batch_start + TOKEN_AUTO_REFRESH_MAX_PARALLEL < len(due_ids):
            await asyncio.sleep(TOKEN_AUTO_REFRESH_BATCH_DELAY_SECONDS)


async def _background_sync_loop(
    session_factory: Any, stop_event: asyncio.Event
) -> None:
    while not stop_event.is_set():
        try:
            await run_token_refresh_cycle(session_factory)
            await run_sync_cycle(session_factory)
        except Exception as exc:
            logger.exception(
                "Background sync loop error while running sync cycle: %s",
                exc,
            )
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=SYNC_LOOP_INTERVAL_SECONDS
            )
        except TimeoutError:
            continue


def start_background_sync_worker(session_factory: Any) -> None:
    global _BACKGROUND_TASK, _STOP_EVENT
    if _BACKGROUND_TASK and not _BACKGROUND_TASK.done():
        return
    _STOP_EVENT = asyncio.Event()
    _BACKGROUND_TASK = asyncio.create_task(
        _background_sync_loop(session_factory, _STOP_EVENT)
    )


async def stop_background_sync_worker() -> None:
    global _BACKGROUND_TASK, _STOP_EVENT
    if _STOP_EVENT is not None:
        _STOP_EVENT.set()
    if _BACKGROUND_TASK is not None:
        try:
            await _BACKGROUND_TASK
        except asyncio.CancelledError:
            pass
    _BACKGROUND_TASK = None
    _STOP_EVENT = None
