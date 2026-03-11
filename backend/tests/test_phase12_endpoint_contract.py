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
    response = client.get("/api/workspaces/org_001/sync")
    assert response.status_code == 502
    body = response.json()
    assert body["detail"]
