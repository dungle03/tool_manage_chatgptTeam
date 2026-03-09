from app.models import Workspace, Member, Invite


def test_model_fields_exist():
    assert hasattr(Workspace, "org_id")
    assert hasattr(Workspace, "access_token")
    assert hasattr(Workspace, "session_token")
    assert hasattr(Workspace, "last_sync")
    assert hasattr(Member, "invite_date")
    assert hasattr(Member, "remote_id")
    assert hasattr(Invite, "invite_id")
