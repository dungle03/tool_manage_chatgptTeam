from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import UnauthorizedFinding, Workspace
from app.services.events import workspace_event_broker
from app.services.workspace_datetime import serialize_datetime
from app.services.workspace_serializers import build_refresh_hint
from app.services.workspace_summaries import workspace_to_dict
from app.services.workspace_unauthorized import active_unauthorized_count


def calculate_unauthorized_kicked(
    session: Session,
    workspace: Workspace,
    *,
    unauthorized_members: list[dict[str, Any]],
    detected_at: Any,
) -> int:
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
    return max(unauthorized_kicked, 0)


def build_sync_success_payload(
    session: Session,
    workspace: Workspace,
    *,
    remote_members_count: int,
    remote_invites_count: int,
    pending_invites: int,
    unauthorized_members: list[dict[str, Any]],
    unauthorized_kicked: int,
) -> dict[str, Any]:
    unauthorized_active_count_value = active_unauthorized_count(
        session, workspace.org_id
    )
    return {
        "ok": True,
        "members_synced": remote_members_count,
        "invites_synced": remote_invites_count,
        "last_sync": serialize_datetime(workspace.last_sync),
        "unauthorized_detected": len(unauthorized_members),
        "unauthorized_kicked": unauthorized_kicked,
        "updated_summary": workspace_to_dict(
            workspace,
            session,
            pending_invites=pending_invites,
            unauthorized_active_count=unauthorized_active_count_value,
        ),
        "refresh_hint": build_refresh_hint(
            scope="workspace_detail",
            org_id=workspace.org_id,
            reason="workspace_synced",
            include_details=True,
        ),
    }


def publish_workspace_sync_success(
    workspace: Workspace,
    *,
    trigger: str,
    pending_invites: int,
    payload: dict[str, Any],
) -> None:
    workspace_event_broker.publish(
        "workspace_updated",
        org_id=workspace.org_id,
        trigger=trigger,
        summary={
            "member_count": workspace.member_count,
            "pending_invites": pending_invites,
            "unauthorized_active_count": payload["updated_summary"].get(
                "unauthorized_active_count", 0
            ),
            "status": workspace.status,
            "last_sync": payload["last_sync"],
        },
    )


def publish_workspace_sync_failure(
    *,
    org_id: str,
    trigger: str,
    error_message: str,
) -> None:
    workspace_event_broker.publish(
        "sync_failed",
        org_id=org_id,
        trigger=trigger,
        error={"message": error_message},
    )
