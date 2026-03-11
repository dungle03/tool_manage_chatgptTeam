from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Invite, Workspace
from app.services.events import workspace_event_broker
from app.services.workspace_sync import (
    list_stale_workspace_ids,
    pick_due_workspaces,
    schedule_followup_sync,
    sync_workspace_data,
)

client = TestClient(app)


def test_list_stale_workspace_ids_includes_null_last_sync():
    session = SessionLocal()
    try:
        workspace = Workspace(
            org_id="org_stale_001",
            account_id="acc_stale_001",
            name="Stale Team",
            status="live",
            member_count=0,
            member_limit=7,
            last_sync=None,
        )
        session.add(workspace)
        session.commit()

        stale_ids = list_stale_workspace_ids(session)
        assert "org_stale_001" in stale_ids
    finally:
        session.close()


def test_list_stale_workspace_ids_prioritizes_pending_invites(seed_data):
    session = SessionLocal()
    try:
        workspace = session.query(Workspace).filter(Workspace.org_id == "org_001").one()
        workspace.last_sync = datetime.now(timezone.utc) - timedelta(seconds=90)
        session.add(
            Invite(
                org_id="org_001",
                email="followup@company.com",
                invite_id="inv_followup_1",
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

        stale_ids = list_stale_workspace_ids(session)
        assert "org_001" in stale_ids
    finally:
        session.close()


def test_sync_workspace_data_updates_workspace_and_emits_event(seed_data, monkeypatch):
    events: list[dict] = []
    original_publish = workspace_event_broker.publish

    def capture_publish(event_type: str, **payload):
        event = original_publish(event_type, **payload)
        events.append(event)
        return event

    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_get_members(_self, _access_token, _account_id):
        return [
            {
                "id": "user_sync_1",
                "email": "sync-user@company.com",
                "name": "Sync User",
                "role": "standard-user",
                "created": "2026-03-09T00:00:00Z",
            }
        ]

    async def fake_get_invites(_self, _access_token, _account_id):
        return [
            {
                "id": "inv_sync_1",
                "email": "invite-sync@company.com",
                "created_at": "2026-03-09T00:00:00Z",
                "status": "pending",
            }
        ]

    monkeypatch.setattr("app.services.events.workspace_event_broker.publish", capture_publish)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_members", fake_get_members)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites)

    session = SessionLocal()
    try:
        workspace = session.query(Workspace).filter(Workspace.org_id == "org_001").one()
        payload = __import__("asyncio").run(sync_workspace_data(session, workspace, trigger="manual"))
        assert payload["ok"] is True
        assert any(event["type"] == "sync_started" for event in events)
        assert any(event["type"] == "workspace_updated" for event in events)
        session.refresh(workspace)
        assert workspace.status == "live"
        assert workspace.sync_error is None
        assert workspace.sync_finished_at is not None
        assert workspace.next_sync_at is not None
        assert workspace.sync_reason in {"followup:0", "pending_invite_watch", "baseline_refresh"}
        assert any(event["type"] == "workspace_scheduled" for event in events)
    finally:
        session.close()


def test_schedule_followup_sync_marks_workspace_hot(seed_data):
    session = SessionLocal()
    try:
        workspace = session.query(Workspace).filter(Workspace.org_id == "org_001").one()
        schedule_followup_sync(session, workspace, reason="invite_created", delay_seconds=5)
        session.commit()
        session.refresh(workspace)

        assert workspace.next_sync_at is not None
        assert workspace.hot_until is not None
        assert workspace.last_activity_at is not None
        assert workspace.sync_reason == "invite_created"
        assert workspace.sync_priority >= 10
    finally:
        session.close()


def test_pick_due_workspaces_prioritizes_hot_and_pending(seed_data):
    session = SessionLocal()
    try:
        hot_workspace = session.query(Workspace).filter(Workspace.org_id == "org_001").one()
        cold_workspace = Workspace(
            org_id="org_cold_001",
            account_id="acc_cold_001",
            name="Cold Team",
            status="live",
            member_count=0,
            member_limit=7,
            last_sync=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        session.add(cold_workspace)
        session.commit()

        schedule_followup_sync(session, hot_workspace, reason="invite_created", delay_seconds=0)
        session.add(
            Invite(
                org_id="org_001",
                email="pending-priority@company.com",
                invite_id="inv_priority_1",
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

        due_workspaces = pick_due_workspaces(session, limit=5)
        assert due_workspaces
        assert due_workspaces[0].org_id == "org_001"
    finally:
        session.close()


def test_invite_route_schedules_followup(seed_data, monkeypatch):
    scheduled: list[dict[str, str]] = []

    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_send_invite(_self, _access_token, _account_id, _email):
        return {"id": "inv_route_1"}

    def fake_schedule_followup_sync(session, workspace, *, reason, delay_seconds=None, hot_window_seconds=None, publish_event=True):
        scheduled.append({"org_id": workspace.org_id, "reason": reason})

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite)
    monkeypatch.setattr("app.routers.invites.schedule_followup_sync", fake_schedule_followup_sync)

    response = client.post(
        "/api/invite",
        json={"org_id": "org_001", "email": "new-member@company.com", "role": "member"},
    )

    assert response.status_code == 200
    assert scheduled == [{"org_id": "org_001", "reason": "invite_created"}]


def test_workspace_events_stream_requires_auth_when_admin_token_set(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret-token")
    response = client.get("/api/events/workspaces")
    assert response.status_code == 401


def test_workspace_events_path_is_registered_in_openapi():
    paths = set(app.openapi()["paths"].keys())
    assert "/api/events/workspaces" in paths
