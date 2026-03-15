import asyncio

import pytest

from app.main import app
from app.routers.workspaces import _parse_datetime



def test_sync_workspace_fetches_remote_and_updates_cache(client, seed_data, monkeypatch):
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

    response = client.post("/api/workspaces/org_001/sync")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["members_synced"] == 1
    assert data["invites_synced"] == 1


def test_sync_workspace_prefers_created_time_and_normalizes_to_utc(client, seed_data, monkeypatch):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_get_members(_self, _access_token, _account_id):
        return [
            {
                "id": "user_timezone_case",
                "email": "timezone@company.com",
                "name": "Timezone Case",
                "role": "standard-user",
                "created_time": "2026-03-09T15:30:00+07:00",
                "created_at": "2026-03-09T02:00:00Z",
                "created": "2026-03-09T03:00:00Z",
            }
        ]

    async def fake_get_invites(_self, _access_token, _account_id):
        return []

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.refresh_access_token",
        fake_refresh_access_token,
    )
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_members", fake_get_members)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites)

    sync_response = client.post("/api/workspaces/org_001/sync")
    assert sync_response.status_code == 200

    members_response = client.get("/api/workspaces/org_001/members")
    assert members_response.status_code == 200

    members = members_response.json()
    assert len(members) == 1
    assert members[0]["created_at"] == "2026-03-09T08:30:00+00:00"


@pytest.mark.parametrize(
    "member_payload, expected_created_at",
    [
        (
            {
                "id": "user_case_1",
                "email": "case1@company.com",
                "name": "Case One",
                "role": "standard-user",
                "created_time": "2026-03-09T01:00:00Z",
                "created_at": "2026-03-09T02:00:00Z",
                "created": "2026-03-09T03:00:00Z",
            },
            "2026-03-09T01:00:00+00:00",
        ),
        (
            {
                "id": "user_case_2",
                "email": "case2@company.com",
                "name": "Case Two",
                "role": "standard-user",
                "created_at": "2026-03-09T04:00:00Z",
                "created": "2026-03-09T05:00:00Z",
            },
            "2026-03-09T04:00:00+00:00",
        ),
        (
            {
                "id": "user_case_3",
                "email": "case3@company.com",
                "name": "Case Three",
                "role": "standard-user",
                "created": "2026-03-09T06:00:00Z",
            },
            "2026-03-09T06:00:00+00:00",
        ),
    ],
)
def test_sync_workspace_uses_expected_date_field_priority(
    client,
    seed_data,
    monkeypatch,
    member_payload,
    expected_created_at,
):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_get_members(_self, _access_token, _account_id):
        return [member_payload]

    async def fake_get_invites(_self, _access_token, _account_id):
        return []

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.refresh_access_token",
        fake_refresh_access_token,
    )
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_members", fake_get_members)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites)

    sync_response = client.post("/api/workspaces/org_001/sync")
    assert sync_response.status_code == 200

    members_response = client.get("/api/workspaces/org_001/members")
    assert members_response.status_code == 200

    members = members_response.json()
    assert len(members) == 1
    assert members[0]["created_at"] == expected_created_at


def test_parse_datetime_accepts_epoch_seconds():
    parsed = _parse_datetime(1741516200)

    assert parsed is not None
    assert parsed.isoformat() == "2025-03-09T10:30:00+00:00"


def test_parse_datetime_accepts_epoch_milliseconds():
    parsed = _parse_datetime(1741516200000)

    assert parsed is not None
    assert parsed.isoformat() == "2025-03-09T10:30:00+00:00"


def test_parse_datetime_returns_none_for_invalid_values():
    assert _parse_datetime("not-a-date") is None
    assert _parse_datetime("") is None

