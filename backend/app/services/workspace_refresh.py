import asyncio
import contextlib
import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Workspace
from app.services.events import workspace_event_broker
from app.services.token_refresher import (
    TokenRefreshError,
    get_workspace_token_refresh_lock,
    is_workspace_token_refresh_in_progress,
    mark_workspace_refresh_failure,
    mark_workspace_refresh_success,
    run_token_refresher_for_workspace,
    verify_refreshed_token_for_workspace,
)
from app.services.workspace_sync import (
    build_refresh_hint,
    sync_workspace_data,
    workspace_to_dict,
)

logger = logging.getLogger(__name__)
_WORKSPACE_REFRESH_TASKS: dict[str, asyncio.Task[None]] = {}


def track_workspace_refresh_task(org_id: str, task: asyncio.Task[None]) -> None:
    _WORKSPACE_REFRESH_TASKS[org_id] = task

    def _cleanup(completed_task: asyncio.Task[None]) -> None:
        current_task = _WORKSPACE_REFRESH_TASKS.get(org_id)
        if current_task is completed_task:
            _WORKSPACE_REFRESH_TASKS.pop(org_id, None)
        with contextlib.suppress(asyncio.CancelledError):
            exc = completed_task.exception()
            if exc is not None:
                logger.exception(
                    "Background workspace token refresh task crashed for workspace=%s",
                    org_id,
                    exc_info=exc,
                )

    task.add_done_callback(_cleanup)


async def run_workspace_token_refresh_job(org_id: str) -> None:
    session = SessionLocal()
    try:
        workspace = session.execute(
            select(Workspace).where(Workspace.org_id == org_id)
        ).scalar_one_or_none()
        if workspace is None:
            logger.warning(
                "background refresh-token workspace not found for workspace=%s", org_id
            )
            return

        refresh_lock = get_workspace_token_refresh_lock(workspace.org_id)
        async with refresh_lock:
            logger.info(
                "background refresh-token started for workspace=%s", workspace.org_id
            )
            try:
                refresh_result = await run_token_refresher_for_workspace(
                    session, workspace, mode="manual"
                )
                verified_result = await verify_refreshed_token_for_workspace(
                    workspace, refresh_result
                )
                mark_workspace_refresh_success(workspace, verified_result)
                session.commit()
                session.refresh(workspace)
                workspace_event_broker.publish(
                    "workspace_token_refreshed",
                    org_id=workspace.org_id,
                    trigger="manual",
                    summary=workspace_to_dict(workspace, session),
                )
            except TokenRefreshError as exc:
                logger.warning(
                    "background refresh-token failed for workspace=%s detail=%s",
                    org_id,
                    exc.message,
                )
                session.rollback()
                managed_workspace = session.execute(
                    select(Workspace).where(Workspace.org_id == org_id)
                ).scalar_one_or_none()
                if managed_workspace is not None:
                    mark_workspace_refresh_failure(
                        managed_workspace,
                        exc.message,
                        mode="manual",
                    )
                    session.commit()
                    session.refresh(managed_workspace)
                    workspace_event_broker.publish(
                        "workspace_token_refresh_failed",
                        org_id=managed_workspace.org_id,
                        trigger="manual",
                        summary=workspace_to_dict(managed_workspace, session),
                        error={"message": exc.message},
                    )
                return

            try:
                await sync_workspace_data(
                    session,
                    workspace,
                    trigger="manual",
                    publish_events=True,
                )
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                logger.warning(
                    "background refresh-token sync failed for workspace=%s detail=%s",
                    org_id,
                    detail,
                )
                session.rollback()
            finally:
                with contextlib.suppress(Exception):
                    session.refresh(workspace)
    finally:
        session.close()


def build_workspace_refresh_response(
    *,
    workspace: Workspace,
    session: Session,
    status: str,
    message: str,
    already_in_progress: bool,
    reason: str,
):
    return {
        "ok": True,
        "action": "workspace_token_refresh",
        "status": status,
        "message": message,
        "workspace_id": workspace.org_id,
        "token_updated": False,
        "sync_completed": False,
        "already_in_progress": already_in_progress,
        "updated_summary": workspace_to_dict(workspace, session),
        "refresh_hint": build_refresh_hint(
            scope="workspace_detail",
            org_id=workspace.org_id,
            reason=reason,
            include_details=True,
        ),
    }


def build_in_progress_workspace_refresh_response(
    workspace: Workspace, session: Session
):
    return build_workspace_refresh_response(
        workspace=workspace,
        session=session,
        status="in_progress",
        message="Workspace đang được refresh token",
        already_in_progress=True,
        reason="workspace_token_refresh_in_progress",
    )


def schedule_workspace_token_refresh(workspace: Workspace) -> None:
    task = asyncio.create_task(run_workspace_token_refresh_job(workspace.org_id))
    track_workspace_refresh_task(workspace.org_id, task)


def has_tracked_workspace_refresh_task(org_id: str) -> bool:
    existing_task = _WORKSPACE_REFRESH_TASKS.get(org_id)
    return existing_task is not None and not existing_task.done()


def resolve_workspace_refresh_request(workspace: Workspace, session: Session):
    if has_tracked_workspace_refresh_task(workspace.org_id):
        logger.info(
            "refresh-token background task already tracked for workspace=%s",
            workspace.org_id,
        )
        return build_in_progress_workspace_refresh_response(workspace, session)

    if is_workspace_token_refresh_in_progress(workspace.org_id):
        logger.info(
            "refresh-token already in progress for workspace=%s", workspace.org_id
        )
        return build_in_progress_workspace_refresh_response(workspace, session)

    schedule_workspace_token_refresh(workspace)
    logger.info(
        "refresh-token background task scheduled for workspace=%s", workspace.org_id
    )
    return build_workspace_refresh_response(
        workspace=workspace,
        session=session,
        status="accepted",
        message="Đã đưa yêu cầu refresh token vào hàng đợi xử lý nền",
        already_in_progress=False,
        reason="workspace_token_refresh_started",
    )
