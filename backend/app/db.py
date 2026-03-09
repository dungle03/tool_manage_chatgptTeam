import os

from sqlalchemy import create_engine, inspect, text
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
                    conn.execute(text(f"ALTER TABLE workspaces ADD COLUMN {col} {col_type}"))

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
                    conn.execute(text(f"ALTER TABLE members ADD COLUMN {col} {col_type}"))

        conn.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # Auto-migrate: add any new columns that don't exist yet
    _migrate_add_missing_columns()
