from app.main import app
from app.services import workspace_summaries


def test_get_workspaces_returns_list(client, seed_data):
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["org_id"] == "org_001"
    assert "member_limit" in data[0]
    assert data[0]["pending_invites"] == 1


def test_get_workspaces_reuses_cached_token_metadata(client, seed_data, monkeypatch):
    workspace_summaries._token_metadata_cache.clear()
    decode_calls = 0

    def fake_decode_access_token_claims(access_token):
        nonlocal decode_calls
        decode_calls += 1
        assert access_token == "test-access-token"
        return {
            "exp": 2_000_000_000,
            "sub": "user_remote_owner",
            "email": "owner@company.com",
        }

    monkeypatch.setattr(
        workspace_summaries.chatgpt_service,
        "decode_access_token_claims",
        fake_decode_access_token_claims,
    )

    first_response = client.get("/api/workspaces")
    second_response = client.get("/api/workspaces")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert decode_calls == 1
    assert first_response.json()[0]["current_user_role"] == "owner"
    assert second_response.json()[0]["current_user_role"] == "owner"
