import asyncio
import logging
from typing import Any, Awaitable, Callable

BackgroundCycle = Callable[[Any], Awaitable[None]]


async def run_background_sync_loop(
    session_factory: Any,
    stop_event: asyncio.Event,
    *,
    run_token_refresh_cycle: BackgroundCycle,
    run_sync_cycle: BackgroundCycle,
    loop_interval_seconds: int,
    logger: logging.Logger,
) -> None:
    while not stop_event.is_set():
        try:
            await run_token_refresh_cycle(session_factory)
        except Exception as exc:
            logger.exception(
                "Background sync loop error while running token refresh cycle: %s",
                exc,
            )

        try:
            await run_sync_cycle(session_factory)
        except Exception as exc:
            logger.exception(
                "Background sync loop error while running sync cycle: %s",
                exc,
            )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=loop_interval_seconds)
        except TimeoutError:
            continue
