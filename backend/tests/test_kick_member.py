from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_kick_member_sets_removed_status(seed_data):
    payload = {"org_id": "org_001", "member_id": 1}
    response = client.request("DELETE", "/api/member", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "removed"
