import asyncio

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.auth import verify_admin_token
from app.services.events import format_sse, workspace_event_broker

router = APIRouter()


async def verify_sse_admin_token(
    request: Request,
    admin_token: str | None = Query(default=None),
) -> str:
    authorization = request.headers.get("authorization", "")
    if not authorization and admin_token:
        authorization = f"Bearer {admin_token}"
    return await verify_admin_token(authorization=authorization)


@router.get("/api/events/workspaces")
async def stream_workspace_events(
    request: Request,
    _token: str = Depends(verify_sse_admin_token),
):
    queue = workspace_event_broker.subscribe()

    async def event_stream():
        try:
            initial = workspace_event_broker.make_event("heartbeat")
            yield format_sse(initial)
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                except TimeoutError:
                    event = workspace_event_broker.make_event("heartbeat")
                yield format_sse(event)
        finally:
            workspace_event_broker.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
