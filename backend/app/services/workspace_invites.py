from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Invite, Workspace
from app.services.workspace_datetime import parse_datetime
from app.services.workspace_serializers import normalize_invite_status


def sync_remote_invites(
    session: Session,
    workspace: Workspace,
    remote_invites: list[dict[str, Any]],
    *,
    synced_member_emails: set[str],
) -> None:
    existing_invites = (
        session.execute(select(Invite).where(Invite.org_id == workspace.org_id))
        .scalars()
        .all()
    )
    invites_by_id = {
        invite.invite_id: invite for invite in existing_invites if invite.invite_id
    }
    invites_by_email = {
        invite.email.strip().lower(): invite
        for invite in existing_invites
        if invite.email
    }
    seen_invite_row_ids: set[int] = set()

    for index, item in enumerate(remote_invites, start=1):
        invite_id = str(
            item.get("id") or item.get("invite_id") or f"inv_{workspace.org_id}_{index}"
        )
        email = item.get("email") or item.get("email_address") or ""
        normalized_email = email.strip().lower()
        created_at = parse_datetime(item.get("created_at") or item.get("created"))
        existing_invite = invites_by_id.get(invite_id)
        if existing_invite is None and normalized_email:
            existing_invite = invites_by_email.get(normalized_email)

        if existing_invite:
            existing_invite.email = email
            existing_invite.invite_id = invite_id
            existing_invite.status = normalize_invite_status(
                item.get("status") or "pending"
            )
            existing_invite.created_at = created_at or existing_invite.created_at
            seen_invite_row_ids.add(existing_invite.id)
        else:
            invite = Invite(
                org_id=workspace.org_id,
                email=email,
                invite_id=invite_id,
                status=normalize_invite_status(item.get("status") or "pending"),
                created_by_tool=False,
                created_at=created_at or datetime.now(timezone.utc),
            )
            session.add(invite)
            session.flush()
            seen_invite_row_ids.add(invite.id)

    for existing_invite in existing_invites:
        normalized_existing_email = (existing_invite.email or "").strip().lower()
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
