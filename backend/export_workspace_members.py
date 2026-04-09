import argparse
import csv
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Member, Workspace


@dataclass
class ExportRow:
    team_name: str
    team_id: str
    team_expires_at: str
    member_name: str
    member_email: str
    member_role: str
    member_joined_at: str


def iso_or_empty(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def collect_rows(include_empty_teams: bool = False) -> list[ExportRow]:
    session = SessionLocal()
    try:
        workspaces = (
            session.execute(
                select(Workspace).order_by(Workspace.name, Workspace.org_id)
            )
            .scalars()
            .all()
        )
        rows: list[ExportRow] = []

        for workspace in workspaces:
            members = (
                session.execute(
                    select(Member)
                    .where(Member.org_id == workspace.org_id)
                    .order_by(Member.role, Member.name, Member.email)
                )
                .scalars()
                .all()
            )

            if not members and include_empty_teams:
                rows.append(
                    ExportRow(
                        team_name=workspace.name,
                        team_id=workspace.org_id,
                        team_expires_at=iso_or_empty(workspace.expires_at),
                        member_name="",
                        member_email="",
                        member_role="",
                        member_joined_at="",
                    )
                )
                continue

            for member in members:
                rows.append(
                    ExportRow(
                        team_name=workspace.name,
                        team_id=workspace.org_id,
                        team_expires_at=iso_or_empty(workspace.expires_at),
                        member_name=member.name or "",
                        member_email=member.email or "",
                        member_role=member.role or "",
                        member_joined_at=iso_or_empty(
                            member.created_at or member.invite_date
                        ),
                    )
                )

        return rows
    finally:
        session.close()


def export_csv(rows: list[ExportRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        list(asdict(rows[0]).keys())
        if rows
        else list(ExportRow.__dataclass_fields__.keys())
    )
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def export_json(rows: list[ExportRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(row) for row in rows]
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export teams and members from the local workspace manager database.",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "json"),
        default="csv",
        help="Output format. Default: csv",
    )
    parser.add_argument(
        "--output",
        default="exports/team_members_export.csv",
        help="Output file path. Default: exports/team_members_export.csv",
    )
    parser.add_argument(
        "--include-empty-teams",
        action="store_true",
        help="Include teams that currently have no member rows in the database.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL override. By default uses DATABASE_URL or the local SQLite DB.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    rows = collect_rows(include_empty_teams=args.include_empty_teams)
    output_path = Path(args.output)

    if args.format == "json":
        export_json(rows, output_path)
    else:
        export_csv(rows, output_path)

    print(f"Exported {len(rows)} row(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
