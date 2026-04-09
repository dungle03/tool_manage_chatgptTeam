import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.models import Workspace

SYNC_STALE_MINUTES = int(os.getenv("SYNC_STALE_MINUTES", "5"))
SYNC_PENDING_INVITE_SECONDS = int(os.getenv("SYNC_PENDING_INVITE_SECONDS", "15"))
SYNC_BASELINE_MINUTES = int(os.getenv("SYNC_BASELINE_MINUTES", str(SYNC_STALE_MINUTES)))
SYNC_HOT_WINDOW_SECONDS = int(os.getenv("SYNC_HOT_WINDOW_SECONDS", "180"))


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


def normalize_schedule_datetime(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def step_index_from_reason(reason: str | None) -> int:
    if not reason or not reason.startswith("followup:"):
        return -1
    try:
        return int(reason.split(":", 1)[1])
    except ValueError:
        return -1


def compute_workspace_priority(
    workspace: Workspace, pending_invites: int, now: datetime
) -> int:
    hot_until = normalize_schedule_datetime(workspace.hot_until)
    if workspace.status == "error":
        return 80
    if pending_invites > 0:
        return 100
    if hot_until and hot_until > now:
        return 90
    return 10


def build_followup_schedule_update(
    workspace: Workspace,
    *,
    now: datetime,
    reason: str,
    pending_invites: int,
    delay_seconds: int | None = None,
    hot_window_seconds: int | None = None,
) -> dict[str, Any]:
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

    current_hot_until = normalize_schedule_datetime(workspace.hot_until)
    current_next_sync_at = normalize_schedule_datetime(workspace.next_sync_at)
    return {
        "last_activity_at": now,
        "hot_until": (
            max(current_hot_until, hot_until) if current_hot_until else hot_until
        ),
        "next_sync_at": (
            min(current_next_sync_at, next_sync_at)
            if current_next_sync_at is not None
            else next_sync_at
        ),
        "sync_reason": reason,
        "sync_priority": compute_workspace_priority(workspace, pending_invites, now),
    }


def build_baseline_schedule_update(
    workspace: Workspace,
    *,
    now: datetime,
    pending_invites: int,
) -> dict[str, Any]:
    return {
        "hot_until": None,
        "next_sync_at": now + timedelta(minutes=SYNC_BASELINE_MINUTES),
        "sync_reason": "baseline_refresh",
        "sync_priority": compute_workspace_priority(workspace, pending_invites, now),
    }


def build_next_sync_after_success_update(
    workspace: Workspace,
    *,
    pending_invites: int,
    last_sync: datetime | None,
) -> dict[str, Any]:
    effective_last_sync = normalize_schedule_datetime(last_sync) or datetime.now(
        timezone.utc
    )

    if pending_invites > 0:
        return build_followup_schedule_update(
            workspace,
            now=effective_last_sync,
            reason="pending_invite_watch",
            pending_invites=pending_invites,
            delay_seconds=SYNC_PENDING_INVITE_SECONDS,
        )

    hot_until = normalize_schedule_datetime(workspace.hot_until)
    current_step_index = step_index_from_reason(workspace.sync_reason)
    has_active_hot_window = bool(hot_until and hot_until > effective_last_sync)

    if has_active_hot_window:
        next_step_index = current_step_index + 1
        if 0 <= next_step_index < len(SYNC_FOLLOWUP_STEPS):
            return build_followup_schedule_update(
                workspace,
                now=effective_last_sync,
                reason=f"followup:{next_step_index}",
                pending_invites=pending_invites,
                delay_seconds=SYNC_FOLLOWUP_STEPS[next_step_index],
            )

    return build_baseline_schedule_update(
        workspace,
        now=effective_last_sync,
        pending_invites=pending_invites,
    )


def build_retry_after_failure_update(
    workspace: Workspace,
    *,
    pending_invites: int,
    now: datetime,
) -> dict[str, Any]:
    return build_followup_schedule_update(
        workspace,
        now=now,
        reason="retry_after_error",
        pending_invites=pending_invites,
        delay_seconds=SYNC_ERROR_RETRY_STEPS[0],
    )
