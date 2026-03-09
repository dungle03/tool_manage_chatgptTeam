from app.models import Workspace, Member, Invite


def test_model_fields_exist():
    assert hasattr(Workspace, "org_id")
    assert hasattr(Member, "invite_date")
    assert hasattr(Invite, "invite_id")
