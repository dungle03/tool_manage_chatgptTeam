import asyncio

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_sync_workspace_fetches_remote_and_updates_cache(seed_data, monkeypatch):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_get_members(_self, _access_token, _account_id):
        return [
            {
                "id": "user_1",
                "email": "remote-user@company.com",
                "name": "Remote User",
                "role": "standard-user",
                "created": "2026-03-09T00:00:00Z",
            }
        ]

    async def fake_get_invites(_self, _access_token, _account_id):
        return [
            {
                "id": "inv_remote_1",
                "email": "pending-remote@company.com",
                "created_at": "2026-03-09T00:00:00Z",
                "status": "pending",
            }
        ]

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_members", fake_get_members)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites)

    response = client.get("/api/workspaces/org_001/sync")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["members_synced"] == 1
    assert data["invites_synced"] == 1
