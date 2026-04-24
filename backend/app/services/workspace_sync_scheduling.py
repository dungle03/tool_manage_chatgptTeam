from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Workspace
from app.services.events import workspace_event_broker
from app.services.workspace_datetime import coerce_utc, serialize_datetime, utc_now
from app.services.workspace_schedule import (
    build_baseline_schedule_update,
    build_followup_schedule_update,
    build_next_sync_after_success_update,
    build_retry_after_failure_update,
)
from app.services.workspace_summaries import pending_invite_count


def publish_schedule_event(workspace: Workspace, pending_invites: int) -> None:
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


def apply_schedule_update(workspace: Workspace, update: dict[str, Any]) -> None:
    for field_name, value in update.items():
        setattr(workspace, field_name, value)


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
    pending_invites = pending_invite_count(session, workspace.org_id)
    apply_schedule_update(
        workspace,
        build_followup_schedule_update(
            workspace,
            now=now,
            reason=reason,
            pending_invites=pending_invites,
            delay_seconds=delay_seconds,
            hot_window_seconds=hot_window_seconds,
        ),
    )

    if publish_event:
        publish_schedule_event(workspace, pending_invites)


def set_baseline_schedule(
    workspace: Workspace,
    *,
    now: datetime,
    pending_invites: int,
) -> None:
    apply_schedule_update(
        workspace,
        build_baseline_schedule_update(
            workspace,
            now=now,
            pending_invites=pending_invites,
        ),
    )


def schedule_next_sync_after_success(
    workspace: Workspace,
    *,
    pending_invites: int,
) -> None:
    apply_schedule_update(
        workspace,
        build_next_sync_after_success_update(
            workspace,
            pending_invites=pending_invites,
            last_sync=workspace.last_sync,
        ),
    )


def schedule_retry_after_failure(
    session: Session,
    workspace: Workspace,
) -> None:
    apply_schedule_update(
        workspace,
        build_retry_after_failure_update(
            workspace,
            pending_invites=pending_invite_count(session, workspace.org_id),
            now=utc_now(),
        ),
    )
