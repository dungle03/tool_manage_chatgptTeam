from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import app
from app.models import Base, Invite, Member, Workspace

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_session():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_data(db_session):
    workspace = Workspace(org_id="org_001", name="Alpha Team", member_limit=7, created_at=datetime.utcnow())
    member = Member(
        org_id="org_001",
        email="owner@company.com",
        name="Owner",
        role="owner",
        status="active",
        invite_date=datetime.utcnow(),
    )
    invite = Invite(
        org_id="org_001",
        email="invitee@company.com",
        invite_id="inv_seed_1",
        status="pending",
        created_at=datetime.utcnow(),
    )
    db_session.add(workspace)
    db_session.add(member)
    db_session.add(invite)
    db_session.commit()
    return {"workspace": workspace, "member": member, "invite": invite}
