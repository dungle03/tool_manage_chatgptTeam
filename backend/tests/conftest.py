import os
from datetime import datetime, timezone
from pathlib import Path

TEST_DB_PATH = Path(__file__).resolve().parent / f"workspace_manager_test_{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ.setdefault("WORKSPACE_MANAGER_DISABLE_BACKGROUND_SYNC", "1")

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal, engine
from app.main import app
from app.models import Base, Invite, Member, Workspace


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seed_data():
    session = SessionLocal()
    try:
        workspace = Workspace(
            org_id="org_001",
            account_id="acc_001",
            name="Team Alpha",
            access_token="test-access-token",
            session_token="test-session-token",
            status="live",
            member_count=2,
            member_limit=7,
            last_sync=datetime.now(timezone.utc),
        )
        session.add(workspace)
        session.flush()

        member = Member(
            org_id="org_001",
            remote_id="user_remote_1",
            email="member1@company.com",
            name="Member One",
            role="member",
            status="active",
            invite_date=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        owner = Member(
            org_id="org_001",
            remote_id="user_remote_owner",
            email="owner@company.com",
            name="Owner",
            role="owner",
            status="active",
            invite_date=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
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
