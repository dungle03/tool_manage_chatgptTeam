from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_workspace_members_returns_required_fields(seed_data):
    response = client.get("/api/workspaces/org_001/members")
    assert response.status_code == 200
    member = response.json()[0]
    assert set(["name", "email", "invite_date", "role", "status"]).issubset(member.keys())
