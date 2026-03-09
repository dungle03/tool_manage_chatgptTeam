from datetime import datetime, timezone

import pytest

from app.db import SessionLocal, engine
from app.models import Base, Invite, Member, Workspace


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seed_data():
    session = SessionLocal()
    try:
        workspace = Workspace(org_id="org_001", name="Team Alpha", member_limit=7)
        session.add(workspace)
        session.flush()

        member = Member(
            org_id="org_001",
            email="member1@company.com",
            name="Member One",
            role="member",
            status="active",
            invite_date=datetime.now(timezone.utc),
        )
        owner = Member(
            org_id="org_001",
            email="owner@company.com",
            name="Owner",
            role="owner",
            status="active",
            invite_date=datetime.now(timezone.utc),
        )
        invite = Invite(
            org_id="org_001",
            email="pending@company.com",
            invite_id="inv_seed_1",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        session.add_all([member, owner, invite])
        session.commit()
        yield
    finally:
        session.close()
