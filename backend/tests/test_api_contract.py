from app.main import app


def test_required_paths_exist_in_openapi():
    paths = set(app.openapi()["paths"].keys())
    assert "/api/workspaces" in paths
    assert "/api/workspaces/{id}/members" in paths
    assert "/api/invite" in paths
    assert "/api/member" in paths
    assert "/api/invites" in paths
    assert "/api/resend-invite" in paths
    assert "/api/cancel-invite" in paths
