import asyncio
import logging
import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Workspace
from app.services.chatgpt import chatgpt_service
from app.services.events import workspace_event_broker
from app.services.token_refresher import (
    is_workspace_token_refresh_in_progress as is_workspace_token_refresh_in_progress,
    run_token_refresher_for_workspace,
    select_due_token_refresh_workspace_ids,
    verify_refreshed_token_for_workspace,
)
from app.services.workspace_datetime import (
    parse_datetime,
    serialize_datetime,
    utc_now,
)
from app.services.workspace_invites import sync_remote_invites
from app.services.workspace_members import (
    build_authorization_whitelist,
    filter_members_for_cache,
    normalize_member_role,
    rebuild_member_cache,
)
from app.services.workspace_schedule import compute_workspace_priority
from app.services.workspace_summaries import (
    build_workspace_list_payload as build_workspace_list_payload,
    normalize_identity,
    pending_invite_count as _pending_invite_count,
    workspace_to_dict,
)
from app.services.workspace_serializers import (
    build_refresh_hint,
    normalize_invite_status as normalize_invite_status,
    serialize_invite_row as serialize_invite_row,
    serialize_member_row as serialize_member_row,
    serialize_unauthorized_finding_row as serialize_unauthorized_finding_row,
)
from app.services.workspace_sync_background import (
    list_stale_workspace_ids as _list_stale_workspace_ids,
    pick_due_workspaces as _pick_due_workspaces,
    run_sync_cycle as _run_sync_cycle,
)
from app.services.workspace_sync_results import (
    build_sync_success_payload,
    calculate_unauthorized_kicked,
    publish_workspace_sync_failure,
    publish_workspace_sync_success,
)
from app.services.workspace_sync_scheduling import (
    publish_schedule_event,
    schedule_followup_sync as schedule_followup_sync,
    schedule_next_sync_after_success,
    schedule_retry_after_failure,
)
from app.services.workspace_token_refresh_cycle import (
    run_token_refresh_cycle as _run_token_refresh_cycle,
)
from app.services.workspace_sync_worker import run_background_sync_loop
from app.services.workspace_unauthorized import process_remote_member_authorization

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


SYNC_FOLLOWUP_STEPS = [5, 15, 30, 60]


def _get_workspace_lock(org_id: str) -> asyncio.Lock:
    lock = _SYNC_LOCKS.get(org_id)
    if lock is None:
        lock = asyncio.Lock()
        _SYNC_LOCKS[org_id] = lock
    return lock


def is_workspace_sync_in_progress(org_id: str) -> bool:
    return _get_workspace_lock(org_id).locked()


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
    schedule_retry_after_failure(session, managed_workspace)
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


async def resolve_access_token(workspace: Workspace) -> str:
    if workspace.access_token:
        return workspace.access_token

    raise HTTPException(status_code=400, detail="workspace missing access token")


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
        workspace.sync_priority = compute_workspace_priority(
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

            whitelisted_remote_ids, whitelisted_emails = build_authorization_whitelist(
                session,
                workspace,
                normalize_identity=normalize_identity,
            )

            detected_at = utc_now()
            authorization_result = await process_remote_member_authorization(
                session,
                workspace=workspace,
                remote_members=remote_members,
                whitelisted_remote_ids=whitelisted_remote_ids,
                whitelisted_emails=whitelisted_emails,
                detected_at=detected_at,
                access_token=access_token,
                account_id=account_id,
                delete_member=chatgpt_service.delete_member,
                normalize_member_role=normalize_member_role,
                parse_datetime=parse_datetime,
            )
            normalized_remote_members = authorization_result[
                "normalized_remote_members"
            ]
            unauthorized_members = authorization_result["unauthorized_members"]
            auto_kicked_remote_ids = authorization_result["auto_kicked_remote_ids"]

            synced_members_for_cache = filter_members_for_cache(
                normalized_remote_members,
                auto_kicked_remote_ids,
                normalize_identity=normalize_identity,
            )
            synced_member_emails = rebuild_member_cache(
                session,
                workspace,
                synced_members_for_cache,
            )

            sync_remote_invites(
                session,
                workspace,
                remote_invites,
                synced_member_emails=synced_member_emails,
            )

            workspace.member_count = len(synced_members_for_cache)
            workspace.last_sync = utc_now()
            workspace.sync_finished_at = workspace.last_sync
            workspace.status = "live"
            workspace.sync_error = None
            pending_invites = _pending_invite_count(session, workspace.org_id)
            unauthorized_kicked = calculate_unauthorized_kicked(
                session,
                workspace,
                unauthorized_members=unauthorized_members,
                detected_at=detected_at,
            )
            schedule_next_sync_after_success(
                workspace,
                pending_invites=pending_invites,
            )

            session.commit()

            payload = build_sync_success_payload(
                session,
                workspace,
                remote_members_count=len(remote_members),
                remote_invites_count=len(remote_invites),
                pending_invites=pending_invites,
                unauthorized_members=unauthorized_members,
                unauthorized_kicked=unauthorized_kicked,
            )
            if publish_events:
                publish_workspace_sync_success(
                    workspace,
                    trigger=trigger,
                    pending_invites=pending_invites,
                    payload=payload,
                )
                publish_schedule_event(workspace, pending_invites)
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
                failure_message = (
                    failed_workspace.sync_error
                    if failed_workspace is not None
                    else (
                        exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                    )
                )
                publish_workspace_sync_failure(
                    org_id=workspace_org_id,
                    trigger=trigger,
                    error_message=failure_message,
                )
                if failed_workspace is not None:
                    publish_schedule_event(
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
                failure_message = (
                    failed_workspace.sync_error
                    if failed_workspace is not None
                    else str(exc)
                )
                publish_workspace_sync_failure(
                    org_id=workspace_org_id,
                    trigger=trigger,
                    error_message=failure_message,
                )
                if failed_workspace is not None:
                    publish_schedule_event(
                        failed_workspace,
                        _pending_invite_count(session, workspace_org_id),
                    )
            raise HTTPException(
                status_code=502,
                detail=f"workspace sync failed: {exc}",
            ) from exc


def list_stale_workspace_ids(session: Session) -> list[str]:
    return _list_stale_workspace_ids(
        session,
        is_sync_in_progress=is_workspace_sync_in_progress,
        baseline_minutes=SYNC_BASELINE_MINUTES,
        pending_invite_seconds=SYNC_PENDING_INVITE_SECONDS,
    )


def pick_due_workspaces(session: Session, *, limit: int) -> list[Workspace]:
    return _pick_due_workspaces(
        session,
        limit=limit,
        is_sync_in_progress=is_workspace_sync_in_progress,
        baseline_minutes=SYNC_BASELINE_MINUTES,
        pending_invite_seconds=SYNC_PENDING_INVITE_SECONDS,
    )


async def run_sync_cycle(session_factory: Any) -> None:
    await _run_sync_cycle(
        session_factory,
        sync_workspace_data=sync_workspace_data,
        is_sync_in_progress=is_workspace_sync_in_progress,
        max_parallel_workspaces=SYNC_MAX_PARALLEL_WORKSPACES,
        baseline_minutes=SYNC_BASELINE_MINUTES,
        pending_invite_seconds=SYNC_PENDING_INVITE_SECONDS,
    )


async def run_token_refresh_cycle(session_factory: Any) -> None:
    await _run_token_refresh_cycle(
        session_factory,
        sync_workspace_data=sync_workspace_data,
        is_workspace_sync_in_progress=is_workspace_sync_in_progress,
        max_parallel_refreshes=TOKEN_AUTO_REFRESH_MAX_PARALLEL,
        batch_delay_seconds=TOKEN_AUTO_REFRESH_BATCH_DELAY_SECONDS,
        select_due_workspace_ids=select_due_token_refresh_workspace_ids,
        run_token_refresher=run_token_refresher_for_workspace,
        verify_refreshed_token=verify_refreshed_token_for_workspace,
    )


async def _background_sync_loop(
    session_factory: Any, stop_event: asyncio.Event
) -> None:
    await run_background_sync_loop(
        session_factory,
        stop_event,
        run_token_refresh_cycle=run_token_refresh_cycle,
        run_sync_cycle=run_sync_cycle,
        loop_interval_seconds=SYNC_LOOP_INTERVAL_SECONDS,
        logger=logger,
    )


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
