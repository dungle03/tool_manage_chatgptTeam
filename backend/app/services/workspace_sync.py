import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Invite, Member, Workspace
from app.services.chatgpt import chatgpt_service
from app.services.events import workspace_event_broker

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


def coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _step_index_from_reason(reason: str | None) -> int:
    if not reason or not reason.startswith("followup:"):
        return -1
    try:
        return int(reason.split(":", 1)[1])
    except ValueError:
        return -1


def _priority_for_workspace(workspace: Workspace, pending_invites: int, now: datetime) -> int:
    hot_until = coerce_utc(workspace.hot_until)
    if workspace.status == "error":
        return 80
    if pending_invites > 0:
        return 100
    if hot_until and hot_until > now:
        return 90
    return 10


def _publish_schedule_event(workspace: Workspace, pending_invites: int) -> None:
    workspace_event_broker.publish(
        "workspace_scheduled",
        org_id=workspace.org_id,
        reason=workspace.sync_reason,
        next_sync_at=serialize_datetime(workspace.next_sync_at),
        hot_until=serialize_datetime(workspace.hot_until),
        is_hot=bool(coerce_utc(workspace.hot_until) and coerce_utc(workspace.hot_until) > utc_now()),
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
    effective_delay = delay_seconds if delay_seconds is not None else SYNC_FOLLOWUP_STEPS[0]
    next_sync_at = now + timedelta(seconds=max(0, effective_delay))

    current_hot_until = coerce_utc(workspace.hot_until)
    current_next_sync_at = coerce_utc(workspace.next_sync_at)
    workspace.last_activity_at = now
    workspace.hot_until = max(current_hot_until, hot_until) if current_hot_until else hot_until
    workspace.next_sync_at = (
        min(current_next_sync_at, next_sync_at)
        if current_next_sync_at is not None
        else next_sync_at
    )
    workspace.sync_reason = reason
    workspace.sync_priority = _priority_for_workspace(workspace, pending_invites, now)
    session.flush()

    if publish_event:
        _publish_schedule_event(workspace, pending_invites)



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
    except Exception:
        token_user_id = None

    try:
        token_email = normalize_identity(
            chatgpt_service.extract_email(workspace.access_token)
        )
    except Exception:
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
    account_id = workspace.account_id or workspace.org_id

    if workspace.session_token:
        try:
            refreshed = await chatgpt_service.refresh_access_token(
                workspace.session_token,
                account_id,
            )
            workspace.access_token = refreshed["access_token"]
            workspace.session_token = (
                refreshed.get("session_token") or workspace.session_token
            )
            return workspace.access_token
        except Exception:
            if workspace.access_token:
                return workspace.access_token
            raise

    if workspace.access_token:
        return workspace.access_token

    raise HTTPException(status_code=400, detail="workspace missing access/session token")


def workspace_to_dict(workspace: Workspace, session: Session) -> dict[str, Any]:
    current_user_role = get_current_user_role(workspace, session)
    pending_invites = _pending_invite_count(session, workspace.org_id)
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
        "pending_invites": pending_invites,
        "expires_at": serialize_datetime(workspace.expires_at),
        "last_sync": serialize_datetime(workspace.last_sync),
        "created_at": serialize_datetime(workspace.created_at),
        "current_user_role": current_user_role,
        "can_manage_members": current_user_role in ("owner", "admin"),
        "sync_error": workspace.sync_error,
        "sync_started_at": serialize_datetime(workspace.sync_started_at),
        "sync_finished_at": serialize_datetime(workspace.sync_finished_at),
        "next_sync_at": serialize_datetime(workspace.next_sync_at),
        "hot_until": serialize_datetime(workspace.hot_until),
        "last_activity_at": serialize_datetime(workspace.last_activity_at),
        "sync_reason": workspace.sync_reason,
        "sync_priority": workspace.sync_priority,
        "is_hot": is_hot,
    }


def _pending_invite_count(session: Session, org_id: str) -> int:
    invites = (
        session.execute(select(Invite).where(Invite.org_id == org_id))
        .scalars()
        .all()
    )
    return sum(1 for invite in invites if invite.status == "pending")


async def sync_workspace_data(
    session: Session,
    workspace: Workspace,
    *,
    trigger: str = "manual",
    publish_events: bool = True,
) -> dict[str, Any]:
    lock = _get_workspace_lock(workspace.org_id)
    if lock.locked():
        raise HTTPException(status_code=409, detail="workspace sync already in progress")

    async with lock:
        now = utc_now()
        workspace.status = "syncing"
        workspace.sync_error = None
        workspace.sync_started_at = now
        workspace.next_sync_at = None
        workspace.sync_priority = _priority_for_workspace(
            workspace, _pending_invite_count(session, workspace.org_id), now
        )
        session.commit()

        if publish_events:
            workspace_event_broker.publish(
                "sync_started",
                org_id=workspace.org_id,
                trigger=trigger,
            )

        account_id = workspace.account_id or workspace.org_id

        try:
            access_token = await resolve_access_token(workspace)
            remote_members, remote_invites = await asyncio.gather(
                chatgpt_service.get_members(access_token, account_id),
                chatgpt_service.get_invites(access_token, account_id),
            )

            if remote_members:
                logger.info("[SYNC] First member raw keys: %s", list(remote_members[0].keys()))
                logger.info("[SYNC] First member raw data: %s", remote_members[0])

            session.query(Member).where(Member.org_id == workspace.org_id).delete()
            session.query(Invite).where(Invite.org_id == workspace.org_id).delete()

            for item in remote_members:
                created_raw = (
                    item.get("created_time")
                    or item.get("created_at")
                    or item.get("created")
                )
                created = parse_datetime(created_raw)
                role = normalize_member_role(item)

                session.add(
                    Member(
                        org_id=workspace.org_id,
                        remote_id=str(item.get("id") or "") or None,
                        email=item.get("email") or "",
                        name=item.get("name") or "",
                        role=role,
                        status=item.get("status") or "active",
                        invite_date=created,
                        created_at=created,
                        picture=item.get("picture"),
                    )
                )

            for index, item in enumerate(remote_invites, start=1):
                created_at = parse_datetime(item.get("created_at") or item.get("created"))
                session.add(
                    Invite(
                        org_id=workspace.org_id,
                        email=item.get("email") or item.get("email_address") or "",
                        invite_id=str(
                            item.get("id")
                            or item.get("invite_id")
                            or f"inv_{workspace.org_id}_{index}"
                        ),
                        status=item.get("status") or "pending",
                        created_at=created_at or datetime.now(timezone.utc),
                    )
                )

            workspace.member_count = len(remote_members)
            workspace.last_sync = utc_now()
            workspace.sync_finished_at = workspace.last_sync
            workspace.status = "live"
            workspace.sync_error = None
            pending_invites = _pending_invite_count(session, workspace.org_id)

            if pending_invites > 0:
                schedule_followup_sync(
                    session,
                    workspace,
                    reason="pending_invite_watch",
                    delay_seconds=SYNC_PENDING_INVITE_SECONDS,
                    publish_event=False,
                )
            else:
                hot_until = coerce_utc(workspace.hot_until)
                current_step_index = _step_index_from_reason(workspace.sync_reason)
                if hot_until and hot_until > workspace.last_sync:
                    next_step_index = current_step_index + 1
                    if 0 <= next_step_index < len(SYNC_FOLLOWUP_STEPS):
                        schedule_followup_sync(
                            session,
                            workspace,
                            reason=f"followup:{next_step_index}",
                            delay_seconds=SYNC_FOLLOWUP_STEPS[next_step_index],
                            publish_event=False,
                        )
                    else:
                        workspace.hot_until = None
                        workspace.next_sync_at = workspace.last_sync + timedelta(
                            minutes=SYNC_BASELINE_MINUTES
                        )
                        workspace.sync_reason = "baseline_refresh"
                        workspace.sync_priority = _priority_for_workspace(
                            workspace, 0, workspace.last_sync
                        )
                else:
                    workspace.hot_until = None
                    workspace.next_sync_at = workspace.last_sync + timedelta(
                        minutes=SYNC_BASELINE_MINUTES
                    )
                    workspace.sync_reason = "baseline_refresh"
                    workspace.sync_priority = _priority_for_workspace(
                        workspace, pending_invites, workspace.last_sync
                    )

            session.commit()

            payload = {
                "ok": True,
                "members_synced": len(remote_members),
                "invites_synced": len(remote_invites),
                "last_sync": serialize_datetime(workspace.last_sync),
            }
            if publish_events:
                workspace_event_broker.publish(
                    "workspace_updated",
                    org_id=workspace.org_id,
                    trigger=trigger,
                    summary={
                        "member_count": workspace.member_count,
                        "pending_invites": pending_invites,
                        "status": workspace.status,
                        "last_sync": payload["last_sync"],
                    },
                )
                _publish_schedule_event(workspace, pending_invites)
            return payload
        except HTTPException as exc:
            workspace.status = "error"
            workspace.sync_error = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            workspace.sync_finished_at = utc_now()
            retry_delay = SYNC_ERROR_RETRY_STEPS[0]
            schedule_followup_sync(
                session,
                workspace,
                reason="retry_after_error",
                delay_seconds=retry_delay,
                publish_event=False,
            )
            session.commit()
            if publish_events:
                workspace_event_broker.publish(
                    "sync_failed",
                    org_id=workspace.org_id,
                    trigger=trigger,
                    error={"message": workspace.sync_error},
                )
                _publish_schedule_event(workspace, _pending_invite_count(session, workspace.org_id))
            raise
        except Exception as exc:
            workspace.status = "error"
            workspace.sync_error = str(exc)
            workspace.sync_finished_at = utc_now()
            retry_delay = SYNC_ERROR_RETRY_STEPS[0]
            schedule_followup_sync(
                session,
                workspace,
                reason="retry_after_error",
                delay_seconds=retry_delay,
                publish_event=False,
            )
            session.commit()
            if publish_events:
                workspace_event_broker.publish(
                    "sync_failed",
                    org_id=workspace.org_id,
                    trigger=trigger,
                    error={"message": workspace.sync_error},
                )
                _publish_schedule_event(workspace, _pending_invite_count(session, workspace.org_id))
            raise HTTPException(status_code=502, detail=str(exc)) from exc


def list_stale_workspace_ids(session: Session) -> list[str]:
    return [workspace.org_id for workspace in pick_due_workspaces(session, limit=10_000)]


def pick_due_workspaces(session: Session, *, limit: int) -> list[Workspace]:
    now = utc_now()
    baseline_cutoff = now - timedelta(minutes=SYNC_BASELINE_MINUTES)
    workspaces = session.execute(select(Workspace).order_by(Workspace.org_id)).scalars().all()
    due_workspaces: list[Workspace] = []

    for workspace in workspaces:
        if _get_workspace_lock(workspace.org_id).locked():
            continue

        pending_invites = _pending_invite_count(session, workspace.org_id)
        next_sync_at = coerce_utc(workspace.next_sync_at)
        last_sync = coerce_utc(workspace.last_sync)

        if next_sync_at and next_sync_at <= now:
            workspace.sync_priority = _priority_for_workspace(workspace, pending_invites, now)
            due_workspaces.append(workspace)
            continue

        if workspace.last_sync is None:
            workspace.sync_reason = workspace.sync_reason or "baseline_refresh"
            workspace.sync_priority = _priority_for_workspace(workspace, pending_invites, now)
            due_workspaces.append(workspace)
            continue

        if pending_invites > 0 and last_sync and last_sync <= now - timedelta(seconds=SYNC_PENDING_INVITE_SECONDS):
            workspace.sync_reason = "pending_invite_watch"
            workspace.sync_priority = _priority_for_workspace(workspace, pending_invites, now)
            due_workspaces.append(workspace)
            continue

        if last_sync and last_sync <= baseline_cutoff:
            workspace.sync_reason = workspace.sync_reason or "baseline_refresh"
            workspace.sync_priority = _priority_for_workspace(workspace, pending_invites, now)
            due_workspaces.append(workspace)

    due_workspaces.sort(
        key=lambda workspace: (
            -int(workspace.sync_priority or 0),
            coerce_utc(workspace.next_sync_at) or datetime.min.replace(tzinfo=timezone.utc),
            coerce_utc(workspace.last_activity_at) or datetime.min.replace(tzinfo=timezone.utc),
            workspace.org_id,
        )
    )
    return due_workspaces[:limit]


async def run_sync_cycle(session_factory: Any) -> None:
    session = session_factory()
    try:
        due_workspaces = pick_due_workspaces(session, limit=SYNC_MAX_PARALLEL_WORKSPACES)
        due_ids = [workspace.org_id for workspace in due_workspaces]
    finally:
        session.close()

    for org_id in due_ids:
        session = session_factory()
        try:
            workspace = session.execute(
                select(Workspace).where(Workspace.org_id == org_id)
            ).scalar_one_or_none()
            if workspace is None:
                continue
            try:
                await sync_workspace_data(session, workspace, trigger="auto", publish_events=True)
            except HTTPException:
                continue
        finally:
            session.close()


async def _background_sync_loop(session_factory: Any, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await run_sync_cycle(session_factory)
            workspace_event_broker.publish("heartbeat")
        except Exception:
            logger.exception("Background sync loop error")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=SYNC_LOOP_INTERVAL_SECONDS)
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
        await _BACKGROUND_TASK
    _BACKGROUND_TASK = None
    _STOP_EVENT = None
