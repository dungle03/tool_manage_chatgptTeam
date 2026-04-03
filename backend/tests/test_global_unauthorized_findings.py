from app.db import SessionLocal
from app.models import UnauthorizedFinding


def test_global_unauthorized_findings_returns_active_only_by_default(client, seed_data):
    session = SessionLocal()
    try:
        session.add_all(
            [
                UnauthorizedFinding(
                    org_id="org_001",
                    remote_id="user_detected",
                    email="detected@company.com",
                    name="Detected User",
                    role="member",
                    status="detected",
                ),
                UnauthorizedFinding(
                    org_id="org_001",
                    remote_id="user_failed",
                    email="failed@company.com",
                    name="Failed User",
                    role="member",
                    status="kick_failed",
                ),
                UnauthorizedFinding(
                    org_id="org_001",
                    remote_id="user_trusted",
                    email="trusted@company.com",
                    name="Trusted User",
                    role="member",
                    status="trusted",
                ),
                UnauthorizedFinding(
                    org_id="org_001",
                    remote_id="user_kicked",
                    email="kicked@company.com",
                    name="Kicked User",
                    role="member",
                    status="kicked",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    response = client.get("/api/unauthorized-findings")
    assert response.status_code == 200, response.text
    data = response.json()

    returned_statuses = {item["status"] for item in data}
    returned_ids = {item["remote_id"] for item in data}

    assert returned_statuses == {"detected", "kick_failed"}
    assert returned_ids == {"user_detected", "user_failed"}


def test_global_unauthorized_findings_can_include_resolved_history(client, seed_data):
    session = SessionLocal()
    try:
        session.add_all(
            [
                UnauthorizedFinding(
                    org_id="org_001",
                    remote_id="user_detected_all",
                    email="detected-all@company.com",
                    name="Detected All",
                    role="member",
                    status="detected",
                ),
                UnauthorizedFinding(
                    org_id="org_001",
                    remote_id="user_trusted_all",
                    email="trusted-all@company.com",
                    name="Trusted All",
                    role="member",
                    status="trusted",
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    response = client.get("/api/unauthorized-findings?include_resolved=true")
    assert response.status_code == 200, response.text
    data = response.json()

    returned_ids = {item["remote_id"] for item in data}
    assert {"user_detected_all", "user_trusted_all"}.issubset(returned_ids)
