"""Seed the database with sample data for development."""

from datetime import datetime, timezone

from app.db import SessionLocal, init_db
from app.models import Invite, Member, Workspace

init_db()

session = SessionLocal()
try:
    # Clear existing
    session.query(Invite).delete()
    session.query(Member).delete()
    session.query(Workspace).delete()
    session.commit()

    # Workspaces
    ws1 = Workspace(org_id="org_001", name="ChatGPT Team Alpha", member_limit=7)
    ws2 = Workspace(org_id="org_002", name="ChatGPT Team Beta", member_limit=5)
    session.add_all([ws1, ws2])
    session.flush()

    # Members for Team Alpha
    members_alpha = [
        Member(
            org_id="org_001",
            email="dung@company.com",
            name="Dung Le",
            role="owner",
            status="active",
            invite_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        ),
        Member(
            org_id="org_001",
            email="minh@company.com",
            name="Minh Tran",
            role="admin",
            status="active",
            invite_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        ),
        Member(
            org_id="org_001",
            email="linh@company.com",
            name="Linh Nguyen",
            role="member",
            status="active",
            invite_date=datetime(2026, 2, 10, tzinfo=timezone.utc),
        ),
        Member(
            org_id="org_001",
            email="hoa@company.com",
            name="Hoa Pham",
            role="member",
            status="active",
            invite_date=datetime(2026, 2, 20, tzinfo=timezone.utc),
        ),
        Member(
            org_id="org_001",
            email="nam@company.com",
            name="Nam Vo",
            role="member",
            status="pending",
            invite_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        ),
    ]

    # Members for Team Beta
    members_beta = [
        Member(
            org_id="org_002",
            email="an@startup.io",
            name="An Le",
            role="owner",
            status="active",
            invite_date=datetime(2026, 1, 20, tzinfo=timezone.utc),
        ),
        Member(
            org_id="org_002",
            email="binh@startup.io",
            name="Binh Tran",
            role="member",
            status="active",
            invite_date=datetime(2026, 2, 5, tzinfo=timezone.utc),
        ),
    ]

    session.add_all(members_alpha + members_beta)

    # Invites
    invites = [
        Invite(
            org_id="org_001",
            email="new1@company.com",
            invite_id="inv_abc123",
            status="pending",
            created_at=datetime.now(timezone.utc),
        ),
        Invite(
            org_id="org_001",
            email="new2@company.com",
            invite_id="inv_def456",
            status="pending",
            created_at=datetime.now(timezone.utc),
        ),
        Invite(
            org_id="org_002",
            email="new3@startup.io",
            invite_id="inv_ghi789",
            status="pending",
            created_at=datetime.now(timezone.utc),
        ),
    ]
    session.add_all(invites)

    session.commit()
    print("✅ Database seeded successfully!")
    print(f"   - 2 workspaces")
    print(f"   - 7 members")
    print(f"   - 3 invites")
finally:
    session.close()
