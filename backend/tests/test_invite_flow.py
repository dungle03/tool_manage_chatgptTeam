from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_invite_then_list_invites(seed_data):
    payload = {"org_id": "org_001", "email": "new@company.com", "role": "member"}
    create_res = client.post("/api/invite", json=payload)
    assert create_res.status_code == 200

    list_res = client.get("/api/invites", params={"org_id": "org_001"})
    assert list_res.status_code == 200
    emails = [x["email"] for x in list_res.json()]
    assert "new@company.com" in emails
