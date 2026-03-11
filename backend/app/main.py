import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import SessionLocal, init_db
from app.routers import events, invites, members, workspaces
from app.services.workspace_sync import (
    start_background_sync_worker,
    stop_background_sync_worker,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_background_sync_worker(SessionLocal)
    try:
        yield
    finally:
        await stop_background_sync_worker()


app = FastAPI(title="Workspace Manager API", lifespan=lifespan)

# CORS - allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspaces.router)
app.include_router(members.router)
app.include_router(invites.router)
app.include_router(events.router)
