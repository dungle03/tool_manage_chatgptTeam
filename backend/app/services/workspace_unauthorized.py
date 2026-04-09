from datetime import datetime
from typing import Any, Awaitable, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import UnauthorizedFinding, Workspace


DeleteMemberCallable = Callable[[str, str, str], Awaitable[None]]


def _normalize_identity(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


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
        "first_seen_at": (
            finding.first_seen_at.isoformat() if finding.first_seen_at else None
        ),
        "last_seen_at": (
            finding.last_seen_at.isoformat() if finding.last_seen_at else None
        ),
        "resolved_at": finding.resolved_at.isoformat() if finding.resolved_at else None,
        "created_at": finding.created_at.isoformat() if finding.created_at else None,
        "updated_at": finding.updated_at.isoformat() if finding.updated_at else None,
    }


def active_unauthorized_statuses() -> tuple[str, ...]:
    return ("detected", "kick_failed")


def build_unauthorized_count_map(
    session: Session,
    org_ids: list[str],
) -> dict[str, int]:
    if not org_ids:
        return {}

    rows = session.execute(
        select(UnauthorizedFinding.org_id, func.count().label("active_count"))
        .where(
            UnauthorizedFinding.org_id.in_(org_ids),
            UnauthorizedFinding.status.in_(active_unauthorized_statuses()),
        )
        .group_by(UnauthorizedFinding.org_id)
    ).all()
    return {str(org_id): int(active_count or 0) for org_id, active_count in rows}


def active_unauthorized_count(session: Session, org_id: str) -> int:
    return int(
        session.execute(
            select(func.count())
            .select_from(UnauthorizedFinding)
            .where(
                UnauthorizedFinding.org_id == org_id,
                UnauthorizedFinding.status.in_(active_unauthorized_statuses()),
            )
        ).scalar_one()
        or 0
    )


def normalize_remote_member(
    item: dict[str, Any],
    *,
    normalize_member_role: Callable[[dict[str, Any]], str],
    parse_datetime: Callable[[str | int | float | datetime | None], datetime | None],
) -> dict[str, Any]:
    created_raw = (
        item.get("created_time") or item.get("created_at") or item.get("created")
    )
    remote_id = (
        item.get("id")
        or item.get("user_id")
        or item.get("member_id")
        or item.get("account_user_id")
    )
    return {
        "remote_id": str(remote_id or "") or None,
        "email": item.get("email") or "",
        "name": item.get("name") or "",
        "role": normalize_member_role(item),
        "status": item.get("status") or "active",
        "created_at": parse_datetime(created_raw),
        "picture": item.get("picture"),
    }


def upsert_unauthorized_finding(
    session: Session,
    *,
    workspace: Workspace,
    member: dict[str, Any],
    detected_at: datetime,
) -> UnauthorizedFinding:
    normalized_email = _normalize_identity(member.get("email")) or ""
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


def mark_missing_findings_resolved(
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
            _normalize_identity(finding.remote_id),
            _normalize_identity(finding.email),
        )
        if finding_key in active_remote_keys:
            continue
        if finding.status in active_unauthorized_statuses():
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


def auto_resolve_stale_finding(
    session: Session,
    *,
    workspace: Workspace,
    remote_id: str | None,
    email: str | None,
    resolved_at: datetime,
) -> None:
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

    filters.append(UnauthorizedFinding.status.in_(active_unauthorized_statuses()))

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


async def process_remote_member_authorization(
    session: Session,
    *,
    workspace: Workspace,
    remote_members: list[dict[str, Any]],
    whitelisted_remote_ids: set[str],
    whitelisted_emails: set[str],
    detected_at: datetime,
    access_token: str,
    account_id: str,
    delete_member: DeleteMemberCallable,
    normalize_member_role: Callable[[dict[str, Any]], str],
    parse_datetime: Callable[[str | int | float | datetime | None], datetime | None],
) -> dict[str, Any]:
    normalized_remote_members = [
        normalize_remote_member(
            item,
            normalize_member_role=normalize_member_role,
            parse_datetime=parse_datetime,
        )
        for item in remote_members
    ]
    unauthorized_members: list[dict[str, Any]] = []
    active_remote_keys: set[tuple[str | None, str | None]] = set()
    auto_kicked_remote_ids: set[str] = set()

    for member in normalized_remote_members:
        remote_id_key = _normalize_identity(member.get("remote_id"))
        email_key = _normalize_identity(member.get("email"))
        active_remote_keys.add((remote_id_key, email_key))
        is_whitelisted = False
        if remote_id_key and remote_id_key in whitelisted_remote_ids:
            is_whitelisted = True
        elif email_key and email_key in whitelisted_emails:
            is_whitelisted = True

        if not is_whitelisted:
            unauthorized_members.append(member)
            finding = upsert_unauthorized_finding(
                session,
                workspace=workspace,
                member=member,
                detected_at=detected_at,
            )
            if workspace.unauthorized_member_mode == "auto_kick":
                remote_id = member.get("remote_id")
                if remote_id and member.get("role") != "owner":
                    try:
                        await delete_member(access_token, account_id, remote_id)
                        finding.status = "kicked"
                        finding.action_reason = "auto_kick_sync_enforcement"
                        finding.resolved_at = detected_at
                        normalized_remote_id = _normalize_identity(remote_id)
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
            auto_resolve_stale_finding(
                session,
                workspace=workspace,
                remote_id=remote_id_key,
                email=email_key,
                resolved_at=detected_at,
            )

    if unauthorized_members:
        workspace.unauthorized_last_detected_at = detected_at

    mark_missing_findings_resolved(
        session,
        workspace=workspace,
        active_remote_keys=active_remote_keys,
        resolved_at=detected_at,
    )

    return {
        "normalized_remote_members": normalized_remote_members,
        "unauthorized_members": unauthorized_members,
        "auto_kicked_remote_ids": auto_kicked_remote_ids,
    }
