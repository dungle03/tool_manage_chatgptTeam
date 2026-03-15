from app.main import app


def test_phase12_required_paths_exist_in_openapi():
    paths = set(app.openapi()["paths"].keys())
    assert "/api/teams/import" in paths
    assert "/api/workspaces/{id}/sync" in paths
    assert "/api/workspaces/{id}/members" in paths


def test_get_workspaces_exposes_phase2_fields(client, seed_data):
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    ws = data[0]
    assert ws["org_id"] == "org_001"
    assert ws["account_id"] == "acc_001"
    assert ws["status"] == "live"
    assert ws["member_count"] == 2
    assert ws["member_limit"] == 7
    assert "last_sync" in ws


def test_workspace_sync_endpoint_has_phase2_shape(client, seed_data):
    response = client.post("/api/workspaces/org_001/sync")
    assert response.status_code == 502
    body = response.json()
    assert body["detail"]


def test_workspace_import_returns_richer_contract(client, monkeypatch):
    async def fake_get_account_info(_self, _access_token):
        return [
            {
                "account_id": "org_import_1",
                "name": "Imported Team",
                "member_limit": 12,
                "expires_at": None,
            }
        ]

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_account_info", fake_get_account_info)

    response = client.post(
        "/api/teams/import",
        json={"access_token": "token-123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["action"] == "workspace_import"
    assert body["refresh_hint"]["scope"] == "workspace_list"
    assert body["refresh_hint"]["reason"] == "workspace_imported"
    assert body["refresh_hint"]["include_details"] is False
    assert body["imported"] == [
        {"id": 1, "org_id": "org_import_1", "name": "Imported Team"}
    ]
    assert len(body["updated_records"]) == 1
    assert body["updated_records"][0]["org_id"] == "org_import_1"
    assert body["updated_records"][0]["name"] == "Imported Team"
    assert body["updated_records"][0]["status"] == "live"
    assert body["schedule_warnings"] == []


def test_workspace_import_returns_partial_success_when_followup_schedule_fails(client, monkeypatch):
    async def fake_get_account_info(_self, _access_token):
        return [
            {
                "account_id": "org_import_warn_1",
                "name": "Imported Warn Team",
                "member_limit": 8,
                "expires_at": None,
            }
        ]

    def fake_schedule_followup_sync(_session, workspace, *, reason, delay_seconds=None, hot_window_seconds=None, publish_event=True):
        if workspace.org_id == "org_import_warn_1":
            raise RuntimeError("schedule phase failed")

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_account_info", fake_get_account_info)
    monkeypatch.setattr("app.routers.workspaces.schedule_followup_sync", fake_schedule_followup_sync)

    response = client.post(
        "/api/teams/import",
        json={"access_token": "token-456"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["imported"] == [
        {"id": 1, "org_id": "org_import_warn_1", "name": "Imported Warn Team"}
    ]
    assert len(body["updated_records"]) == 1
    assert body["updated_records"][0]["org_id"] == "org_import_warn_1"
    assert body["schedule_warnings"] == [
        {
            "org_id": "org_import_warn_1",
            "message": "failed to schedule follow-up sync: schedule phase failed",
        }
    ]
