from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_resend_and_cancel_invite(seed_data):
    resend = client.post("/api/resend-invite", json={"org_id": "org_001", "invite_id": "inv_seed_1"})
    assert resend.status_code == 200
    assert resend.json()["status"] == "pending"

    cancel = client.request("DELETE", "/api/cancel-invite", json={"org_id": "org_001", "invite_id": "inv_seed_1"})
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
