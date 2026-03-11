from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_workspaces_returns_list(seed_data):
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["org_id"] == "org_001"
    assert "member_limit" in data[0]
    assert data[0]["pending_invites"] == 1
