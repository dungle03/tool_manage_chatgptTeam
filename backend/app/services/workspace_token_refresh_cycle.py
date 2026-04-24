import asyncio
import logging
from typing import Any, Awaitable, Callable

from fastapi import HTTPException
from sqlalchemy import select

from app.models import Workspace
from app.services.events import workspace_event_broker
from app.services.token_refresher import (
    TokenRefreshError,
    get_workspace_token_refresh_lock,
    mark_workspace_refresh_failure,
    mark_workspace_refresh_success,
    run_token_refresher_for_workspace,
    select_due_token_refresh_workspace_ids,
    verify_refreshed_token_for_workspace,
)
from app.services.workspace_summaries import workspace_to_dict

logger = logging.getLogger(__name__)

WorkspaceSyncCallback = Callable[..., Awaitable[dict[str, Any]]]
WorkspaceBusyPredicate = Callable[[str], bool]
SelectDueTokenRefreshIds = Callable[[Any], list[str]]
RunTokenRefresher = Callable[..., Awaitable[dict[str, Any]]]
VerifyRefreshedToken = Callable[..., Awaitable[dict[str, Any]]]


async def run_token_refresh_cycle(
    session_factory: Any,
    *,
    sync_workspace_data: WorkspaceSyncCallback,
    is_workspace_sync_in_progress: WorkspaceBusyPredicate,
    max_parallel_refreshes: int,
    batch_delay_seconds: int,
    select_due_workspace_ids: SelectDueTokenRefreshIds = select_due_token_refresh_workspace_ids,
    run_token_refresher: RunTokenRefresher = run_token_refresher_for_workspace,
    verify_refreshed_token: VerifyRefreshedToken = verify_refreshed_token_for_workspace,
) -> None:
    session = session_factory()
    try:
        due_ids = select_due_workspace_ids(session)
    finally:
        session.close()

    if not due_ids:
        return

    async def refresh_one(org_id: str) -> None:
        refresh_lock = get_workspace_token_refresh_lock(org_id)
        if refresh_lock.locked() or is_workspace_sync_in_progress(org_id):
            return

        async with refresh_lock:
            session = session_factory()
            try:
                workspace = session.execute(
                    select(Workspace).where(Workspace.org_id == org_id)
                ).scalar_one_or_none()
                if workspace is None:
                    return
                try:
                    refresh_result = await run_token_refresher(
                        session,
                        workspace,
                        mode="auto",
                    )
                    verified_result = await verify_refreshed_token(
                        workspace, refresh_result
                    )
                    mark_workspace_refresh_success(workspace, verified_result)
                    session.commit()
                    session.refresh(workspace)
                    workspace_event_broker.publish(
                        "workspace_token_refreshed",
                        org_id=workspace.org_id,
                        trigger="auto",
                        summary=workspace_to_dict(workspace, session),
                    )
                    logger.info(
                        "Auto token refresh succeeded for workspace %s",
                        workspace.org_id,
                    )
                except TokenRefreshError as exc:
                    session.rollback()
                    managed_workspace = session.execute(
                        select(Workspace).where(Workspace.org_id == org_id)
                    ).scalar_one_or_none()
                    if managed_workspace is not None:
                        mark_workspace_refresh_failure(
                            managed_workspace,
                            exc.message,
                            mode="auto",
                        )
                        session.commit()
                        session.refresh(managed_workspace)
                        workspace_event_broker.publish(
                            "workspace_token_refresh_failed",
                            org_id=managed_workspace.org_id,
                            trigger="auto",
                            summary=workspace_to_dict(managed_workspace, session),
                            error={"message": exc.message},
                        )
                    logger.warning(
                        "Auto token refresh failed for workspace %s: %s",
                        org_id,
                        exc.message,
                    )
                    return
                except Exception as exc:
                    detail = f"unexpected refresh error: {exc}"
                    session.rollback()
                    managed_workspace = session.execute(
                        select(Workspace).where(Workspace.org_id == org_id)
                    ).scalar_one_or_none()
                    if managed_workspace is not None:
                        mark_workspace_refresh_failure(
                            managed_workspace,
                            detail,
                            mode="auto",
                        )
                        session.commit()
                        session.refresh(managed_workspace)
                        workspace_event_broker.publish(
                            "workspace_token_refresh_failed",
                            org_id=managed_workspace.org_id,
                            trigger="auto",
                            summary=workspace_to_dict(managed_workspace, session),
                            error={"message": detail},
                        )
                    logger.exception(
                        "Auto token refresh crashed for workspace %s",
                        org_id,
                    )
                    return

                try:
                    await sync_workspace_data(
                        session,
                        workspace,
                        trigger="auto",
                        publish_events=True,
                    )
                except HTTPException as exc:
                    logger.warning(
                        "Auto token refresh sync follow-up failed for workspace %s: %s",
                        org_id,
                        exc.detail,
                    )
            finally:
                session.close()

    for batch_start in range(0, len(due_ids), max_parallel_refreshes):
        batch_ids = due_ids[batch_start : batch_start + max_parallel_refreshes]
        await asyncio.gather(*(refresh_one(org_id) for org_id in batch_ids))
        if batch_start + max_parallel_refreshes < len(due_ids):
            await asyncio.sleep(batch_delay_seconds)
