from app.main import app


def test_get_workspaces_returns_list(client, seed_data):
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["org_id"] == "org_001"
    assert "member_limit" in data[0]
