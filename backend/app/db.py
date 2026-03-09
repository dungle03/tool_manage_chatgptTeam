import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import sessionmaker

from app.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./workspace_manager.db")

# SQLite needs check_same_thread=False; PostgreSQL does not
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_index_if_missing(
    conn: Connection, table_name: str, index_name: str, columns: str
) -> None:
    inspector = inspect(conn)
    existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name in existing_indexes:
        return
    conn.execute(text(f"CREATE INDEX {index_name} ON {table_name} ({columns})"))


def _migrate_add_missing_columns() -> None:
    """Add columns that were added in Phase 2 but may not exist in older DBs."""
    inspector = inspect(engine)
    with engine.connect() as conn:
        # workspaces table migrations
        if inspector.has_table("workspaces"):
            existing = {c["name"] for c in inspector.get_columns("workspaces")}
            new_cols = {
                "account_id": "VARCHAR",
                "access_token": "TEXT",
                "session_token": "TEXT",
                "status": "VARCHAR DEFAULT 'live'",
                "member_count": "INTEGER DEFAULT 0",
                "expires_at": "DATETIME",
                "last_sync": "DATETIME",
            }
            for col, col_type in new_cols.items():
                if col not in existing:
                    conn.execute(
                        text(f"ALTER TABLE workspaces ADD COLUMN {col} {col_type}")
                    )

        # members table migrations
        if inspector.has_table("members"):
            existing = {c["name"] for c in inspector.get_columns("members")}
            new_cols = {
                "remote_id": "VARCHAR",
                "created_at": "DATETIME",
                "picture": "VARCHAR",
            }
            for col, col_type in new_cols.items():
                if col not in existing:
                    conn.execute(
                        text(f"ALTER TABLE members ADD COLUMN {col} {col_type}")
                    )

            _create_index_if_missing(
                conn, "members", "ix_members_org_id_id", "org_id, id"
            )
            _create_index_if_missing(
                conn, "members", "ix_members_org_id_remote_id", "org_id, remote_id"
            )

        if inspector.has_table("invites"):
            _create_index_if_missing(
                conn, "invites", "ix_invites_org_id_invite_id", "org_id, invite_id"
            )

        conn.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # Auto-migrate: add any new columns that don't exist yet
    _migrate_add_missing_columns()
