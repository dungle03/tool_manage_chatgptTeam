import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Invite, Workspace
from app.services.workspace_datetime import coerce_utc, utc_now
from app.services.workspace_schedule import compute_workspace_priority
from app.services.workspace_summaries import build_pending_invite_count_map

WorkspaceSyncCallback = Callable[..., Awaitable[dict[str, Any]]]
WorkspaceLockPredicate = Callable[[str], bool]


def list_stale_workspace_ids(
    session: Session,
    *,
    is_sync_in_progress: WorkspaceLockPredicate,
    baseline_minutes: int,
    pending_invite_seconds: int,
) -> list[str]:
    return [
        workspace.org_id
        for workspace in pick_due_workspaces(
            session,
            limit=10_000,
            is_sync_in_progress=is_sync_in_progress,
            baseline_minutes=baseline_minutes,
            pending_invite_seconds=pending_invite_seconds,
        )
    ]


def pick_due_workspaces(
    session: Session,
    *,
    limit: int,
    is_sync_in_progress: WorkspaceLockPredicate,
    baseline_minutes: int,
    pending_invite_seconds: int,
) -> list[Workspace]:
    now = utc_now()
    baseline_cutoff = now - timedelta(minutes=baseline_minutes)
    pending_cutoff = now - timedelta(seconds=pending_invite_seconds)
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
    pending_counts = build_pending_invite_count_map(
        session, [workspace.org_id for workspace in workspaces]
    )
    due_workspaces: list[Workspace] = []

    for workspace in workspaces:
        if is_sync_in_progress(workspace.org_id):
            continue

        pending_invites = pending_counts.get(workspace.org_id, 0)
        next_sync_at = coerce_utc(workspace.next_sync_at)
        last_sync = coerce_utc(workspace.last_sync)

        if next_sync_at and next_sync_at <= now:
            workspace.sync_priority = compute_workspace_priority(
                workspace, pending_invites, now
            )
            due_workspaces.append(workspace)
            continue

        if workspace.last_sync is None:
            workspace.sync_reason = workspace.sync_reason or "baseline_refresh"
            workspace.sync_priority = compute_workspace_priority(
                workspace, pending_invites, now
            )
            due_workspaces.append(workspace)
            continue

        if pending_invites > 0 and last_sync and last_sync <= pending_cutoff:
            workspace.sync_reason = "pending_invite_watch"
            workspace.sync_priority = compute_workspace_priority(
                workspace, pending_invites, now
            )
            due_workspaces.append(workspace)
            continue

        if last_sync and last_sync <= baseline_cutoff:
            workspace.sync_reason = workspace.sync_reason or "baseline_refresh"
            workspace.sync_priority = compute_workspace_priority(
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


async def run_sync_cycle(
    session_factory: Any,
    *,
    sync_workspace_data: WorkspaceSyncCallback,
    is_sync_in_progress: WorkspaceLockPredicate,
    max_parallel_workspaces: int,
    baseline_minutes: int,
    pending_invite_seconds: int,
) -> None:
    session = session_factory()
    try:
        due_workspaces = pick_due_workspaces(
            session,
            limit=max_parallel_workspaces,
            is_sync_in_progress=is_sync_in_progress,
            baseline_minutes=baseline_minutes,
            pending_invite_seconds=pending_invite_seconds,
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
