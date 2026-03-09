from fastapi import FastAPI

from app.routers import invites, members, workspaces

app = FastAPI(title="Workspace Manager API")
app.include_router(workspaces.router)
app.include_router(members.router)
app.include_router(invites.router)
