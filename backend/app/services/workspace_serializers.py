from typing import Any

from app.models import Invite, Member, UnauthorizedFinding
from app.services.workspace_datetime import serialize_datetime
from app.services.workspace_unauthorized import (
    serialize_unauthorized_finding_row as serialize_unauthorized_finding_row_impl,
)


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


def normalize_invite_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"", "0", "1", "2", "3", "4", "5"}:
        numeric_map = {
            "0": "pending",
            "1": "pending",
            "2": "pending",
            "3": "accepted",
            "4": "expired",
            "5": "cancelled",
            "": "pending",
        }
        return numeric_map[normalized]

    if normalized in {"pending", "invited", "open", "sent"}:
        return "pending"
    if normalized in {"accepted", "active", "completed", "joined"}:
        return "accepted"
    if normalized in {"expired", "timeout", "timed_out"}:
        return "expired"
    if normalized in {"cancelled", "canceled", "revoked", "declined"}:
        return "cancelled"

    return normalized or "pending"


def serialize_invite_row(invite: Invite) -> dict[str, Any]:
    return {
        "id": invite.id,
        "org_id": invite.org_id,
        "email": invite.email,
        "invite_id": invite.invite_id,
        "status": normalize_invite_status(invite.status),
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
    payload = serialize_unauthorized_finding_row_impl(finding)
    payload["first_seen_at"] = serialize_datetime(finding.first_seen_at)
    payload["last_seen_at"] = serialize_datetime(finding.last_seen_at)
    payload["resolved_at"] = serialize_datetime(finding.resolved_at)
    payload["created_at"] = serialize_datetime(finding.created_at)
    payload["updated_at"] = serialize_datetime(finding.updated_at)
    return payload
