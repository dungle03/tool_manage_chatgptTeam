from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    account_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="live")
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    member_limit: Mapped[int] = mapped_column(Integer, default=7)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hot_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    sync_priority: Mapped[int] = mapped_column(Integer, default=0)
    unauthorized_member_mode: Mapped[str] = mapped_column(String, default="auto_kick")
    unauthorized_last_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_token_refresh_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_token_refresh_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_refresh_fail_count: Mapped[int] = mapped_column(Integer, default=0)
    token_refresh_blocked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        Index("ix_members_org_id_id", "org_id", "id"),
        Index("ix_members_org_id_remote_id", "org_id", "remote_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, index=True)
    remote_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    invite_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    picture: Mapped[str | None] = mapped_column(String, nullable=True)


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (Index("ix_invites_org_id_invite_id", "org_id", "invite_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    invite_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String)
    created_by_tool: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class UnauthorizedFinding(Base):
    __tablename__ = "unauthorized_findings"
    __table_args__ = (
        Index("ix_unauthorized_findings_org_id_status", "org_id", "status"),
        Index("ix_unauthorized_findings_org_id_email", "org_id", "email"),
        Index(
            "ix_unauthorized_findings_org_id_remote_id",
            "org_id",
            "remote_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, index=True)
    remote_id: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="user")
    status: Mapped[str] = mapped_column(String, default="detected")
    detection_reason: Mapped[str] = mapped_column(
        String, default="missing_from_local_whitelist"
    )
    action_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class PersonalAccount(Base):
    __tablename__ = "personal_accounts"
    __table_args__ = (
        Index("ix_personal_accounts_provider_email", "provider", "email"),
        Index(
            "ix_personal_accounts_provider_account_id",
            "provider",
            "provider_account_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String, default="codex")
    provider_account_id: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String, default="")
    plan_type: Mapped[str] = mapped_column(String, default="unknown")
    subscription_plan: Mapped[str | None] = mapped_column(String, nullable=True)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    plan_renews_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_plan_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_plan_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    plan_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_sync_fail_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="unknown", index=True)
    auth_type: Mapped[str] = mapped_column(String, default="oauth")
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    refresh_token_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_refresh_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reauth_required_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provider_specific_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
