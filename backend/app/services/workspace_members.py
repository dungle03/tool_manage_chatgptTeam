from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Invite, Member, Workspace


NormalizeIdentity = Any


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


def build_authorization_whitelist(
    session: Session,
    workspace: Workspace,
    *,
    normalize_identity: NormalizeIdentity,
) -> tuple[set[str], set[str]]:
    existing_local_members = (
        session.execute(select(Member).where(Member.org_id == workspace.org_id))
        .scalars()
        .all()
    )
    whitelisted_remote_ids = {
        normalized_remote_id
        for member in existing_local_members
        if (normalized_remote_id := normalize_identity(member.remote_id))
    }
    whitelisted_emails = {
        normalized_email
        for member in existing_local_members
        if (normalized_email := normalize_identity(member.email))
    }

    # Only whitelist pending invites that were explicitly created or confirmed
    # via this tool. Remote-only pending invites can be initiated by other
    # members and must not grant authorization.
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
    for invite in pending_invites_rows:
        invite_email = normalize_identity(invite.email)
        if invite_email:
            whitelisted_emails.add(invite_email)

    return whitelisted_remote_ids, whitelisted_emails


def filter_members_for_cache(
    members: list[dict[str, Any]],
    auto_kicked_remote_ids: set[str],
    *,
    normalize_identity: NormalizeIdentity,
) -> list[dict[str, Any]]:
    return [
        member
        for member in members
        if normalize_identity(member.get("remote_id")) not in auto_kicked_remote_ids
    ]


def rebuild_member_cache(
    session: Session,
    workspace: Workspace,
    members: list[dict[str, Any]],
) -> set[str]:
    session.query(Member).where(Member.org_id == workspace.org_id).delete()

    synced_member_emails: set[str] = set()
    for member in members:
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

    return synced_member_emails
