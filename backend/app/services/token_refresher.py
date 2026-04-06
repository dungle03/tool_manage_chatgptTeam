import asyncio
import contextlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Member, Workspace
from app.services.chatgpt import chatgpt_service

logger = logging.getLogger(__name__)

_TOKEN_REFRESH_LOCKS: dict[str, asyncio.Lock] = {}
_AUTO_REFRESH_THRESHOLD = timedelta(
    hours=int(os.getenv("TOKEN_AUTO_REFRESH_THRESHOLD_HOURS", "24"))
)


class TokenRefreshError(Exception):
    def __init__(self, message: str, *, code: str = "token_refresh_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class TokenRefreshInProgressError(TokenRefreshError):
    def __init__(self) -> None:
        super().__init__(
            "Workspace token refresh is already in progress", code="in_progress"
        )


class WorkspaceOwnerNotFoundError(TokenRefreshError):
    def __init__(self) -> None:
        super().__init__("No owner found for this workspace", code="owner_not_found")


class OwnerAccountNotFoundInRefresherError(TokenRefreshError):
    def __init__(self) -> None:
        super().__init__(
            "Owner account not found in refresher", code="owner_not_found_in_refresher"
        )


class TokenWorkspaceMismatchError(TokenRefreshError):
    def __init__(self) -> None:
        super().__init__(
            "Token does not match this workspace", code="token_workspace_mismatch"
        )


class TokenRefreshTimeoutError(TokenRefreshError):
    def __init__(self) -> None:
        super().__init__("Token refresh timed out", code="timeout")


class InvalidRefresherOutputError(TokenRefreshError):
    def __init__(self) -> None:
        super().__init__("Invalid refresher output", code="invalid_output")


class BrowserRefreshFailedError(TokenRefreshError):
    def __init__(self, message: str = "Browser refresh failed") -> None:
        super().__init__(message, code="browser_refresh_failed")


class TokenRefresherConfigError(TokenRefreshError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="config_error")


def _clean_output_snippet(value: str | None, *, limit: int = 280) -> str:
    if not value:
        return ""
    compact = " ".join(part.strip() for part in value.splitlines() if part.strip())
    compact = compact.strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit].rstrip()}..."


def _build_detailed_failure_message(
    base_message: str,
    *,
    stdout: str = "",
    stderr: str = "",
    debug_log_path: Path | None = None,
) -> str:
    detail = _clean_output_snippet(stderr) or _clean_output_snippet(stdout)
    message = f"{base_message}: {detail}" if detail else base_message
    if debug_log_path is not None:
        message = f"{message} | debug_log={debug_log_path}"
    return message


def _refresher_debug_log_dir() -> Path:
    project_root = Path(__file__).resolve().parents[3]
    return project_root / ".brain" / "logs"


def _persist_refresher_debug_output(
    *,
    workspace_id: str,
    owner_email: str,
    mode: str,
    command: list[str],
    return_code: int | None,
    stdout: str,
    stderr: str,
) -> Path | None:
    log_dir = _refresher_debug_log_dir()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_workspace = workspace_id.replace("/", "_")
        log_path = log_dir / (
            f"camoufox_refresh_{safe_workspace}_{timestamp}_{uuid.uuid4().hex[:8]}.log"
        )
        content = "\n".join(
            [
                f"timestamp_utc={datetime.now(timezone.utc).isoformat()}",
                f"workspace_id={workspace_id}",
                f"owner_email={owner_email}",
                f"mode={mode}",
                f"return_code={return_code}",
                f"command={' '.join(command)}",
                "",
                "===== STDOUT =====",
                stdout or "<empty>",
                "",
                "===== STDERR =====",
                stderr or "<empty>",
                "",
            ]
        )
        log_path.write_text(content, encoding="utf-8")
        return log_path
    except OSError:
        logger.exception(
            "Failed to persist token refresher debug output for workspace=%s",
            workspace_id,
        )
        return None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_identity(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def get_workspace_token_refresh_lock(org_id: str) -> asyncio.Lock:
    lock = _TOKEN_REFRESH_LOCKS.get(org_id)
    if lock is None:
        lock = asyncio.Lock()
        _TOKEN_REFRESH_LOCKS[org_id] = lock
    return lock


def is_workspace_token_refresh_in_progress(org_id: str) -> bool:
    return get_workspace_token_refresh_lock(org_id).locked()


async def _resolve_team_account_for_workspace(
    access_token: str, expected_account_id: str | None = None
) -> dict[str, Any]:
    expected_account_key = normalize_identity(expected_account_id)

    try:
        accounts = await chatgpt_service.get_account_info(access_token)
    except Exception as exc:
        raise TokenRefreshError(
            f"failed to verify refreshed token against ChatGPT accounts: {exc}",
            code="account_verification_failed",
        ) from exc

    normalized_accounts: list[tuple[str | None, dict[str, Any]]] = []
    for account in accounts:
        account_id = normalize_identity(str(account.get("account_id") or ""))
        normalized_accounts.append((account_id, account))

    if expected_account_key:
        for account_id, account in normalized_accounts:
            if account_id and account_id == expected_account_key:
                return account
        raise TokenWorkspaceMismatchError()

    if len(normalized_accounts) == 1:
        return normalized_accounts[0][1]

    raise TokenRefreshError(
        "unable to determine the matching ChatGPT team account for this workspace",
        code="account_match_ambiguous",
    )


def _token_refresher_root() -> Path:
    configured = os.getenv("TOKEN_REFRESHER_WORKDIR")
    if configured:
        return Path(configured).expanduser().resolve()
    project_root = Path(__file__).resolve().parents[3]
    return (project_root.parent / "chatgpt_token_refresher").resolve()


def _token_refresher_script() -> Path:
    configured = os.getenv("TOKEN_REFRESHER_SCRIPT")
    if configured:
        return Path(configured).expanduser().resolve()
    return (_token_refresher_root() / "main_camoufox.py").resolve()


def _token_refresher_python() -> str:
    configured = os.getenv("TOKEN_REFRESHER_PYTHON")
    if configured:
        return str(Path(configured).expanduser().resolve())

    search_roots: list[Path] = []
    for candidate_root in [
        _token_refresher_root(),
        _token_refresher_script().resolve().parent,
    ]:
        resolved_root = candidate_root.resolve()
        if resolved_root not in search_roots:
            search_roots.append(resolved_root)

    candidate_paths: list[Path] = []
    for root in search_roots:
        candidate_paths.extend(
            [
                root / ".venv" / "Scripts" / "python.exe",
                root / "venv" / "Scripts" / "python.exe",
                root / ".venv" / "bin" / "python",
                root / "venv" / "bin" / "python",
            ]
        )

    for candidate in candidate_paths:
        if candidate.exists():
            return str(candidate.resolve())

    return sys.executable


def _token_refresher_timeout_seconds(mode: str) -> int:
    env_name = (
        "TOKEN_REFRESHER_AUTO_TIMEOUT_SECONDS"
        if mode == "auto"
        else "TOKEN_REFRESHER_TIMEOUT_SECONDS"
    )
    default_value = "300" if mode == "auto" else "240"
    return max(30, int(os.getenv(env_name, default_value)))


def resolve_workspace_owner_email(session: Session, workspace: Workspace) -> str:
    owners = (
        session.execute(
            select(Member)
            .where(Member.org_id == workspace.org_id)
            .where(Member.role.ilike("owner"))
        )
        .scalars()
        .all()
    )

    candidates = [member for member in owners if normalize_identity(member.email)]
    if not candidates:
        raise WorkspaceOwnerNotFoundError()

    def sort_key(member: Member) -> tuple[datetime, datetime, int]:
        created_at = member.created_at or datetime.max.replace(tzinfo=timezone.utc)
        invite_date = member.invite_date or datetime.max.replace(tzinfo=timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)
        if invite_date.tzinfo is None:
            invite_date = invite_date.replace(tzinfo=timezone.utc)
        else:
            invite_date = invite_date.astimezone(timezone.utc)
        return (created_at, invite_date, int(member.id or 0))

    selected_owner = sorted(candidates, key=sort_key)[0]
    return selected_owner.email.strip()


def _extract_single_result(
    document: dict[str, Any], owner_email: str
) -> dict[str, Any]:
    results = document.get("results")
    if not isinstance(results, list) or not results:
        raise InvalidRefresherOutputError()

    normalized_email = normalize_identity(owner_email)
    for item in results:
        if not isinstance(item, dict):
            continue
        if normalize_identity(str(item.get("email") or "")) == normalized_email:
            return item

    first = results[0]
    if not isinstance(first, dict):
        raise InvalidRefresherOutputError()
    return first


def _read_result_document(output_path: Path, owner_email: str) -> dict[str, Any]:
    if not output_path.exists():
        raise InvalidRefresherOutputError()
    try:
        raw = output_path.read_text(encoding="utf-8")
        document = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidRefresherOutputError() from exc
    if not isinstance(document, dict):
        raise InvalidRefresherOutputError()
    return _extract_single_result(document, owner_email)


def _normalize_refresher_failure(
    *,
    return_code: int,
    stdout: str,
    stderr: str,
    debug_log_path: Path | None = None,
) -> TokenRefreshError:
    combined = "\n".join(
        part for part in [stdout.strip(), stderr.strip()] if part
    ).lower()

    if (
        return_code == 2
        or "không tìm thấy account" in combined
        or "not found account" in combined
    ):
        return OwnerAccountNotFoundInRefresherError()
    if "timed out" in combined or "timeout" in combined:
        return TokenRefreshTimeoutError()
    if "invalid" in combined and "output" in combined:
        return InvalidRefresherOutputError()
    return BrowserRefreshFailedError(
        _build_detailed_failure_message(
            f"Browser refresh failed (exit code {return_code})",
            stdout=stdout,
            stderr=stderr,
            debug_log_path=debug_log_path,
        )
    )


async def run_token_refresher_for_workspace(
    session: Session,
    workspace: Workspace,
    *,
    mode: str = "manual",
) -> dict[str, Any]:
    owner_email = resolve_workspace_owner_email(session, workspace)
    script_path = _token_refresher_script()
    workdir = _token_refresher_root()
    python_executable = _token_refresher_python()

    if not script_path.exists():
        raise TokenRefresherConfigError(
            f"TOKEN_REFRESHER_SCRIPT not found: {script_path}"
        )
    if not workdir.exists():
        raise TokenRefresherConfigError(f"TOKEN_REFRESHER_WORKDIR not found: {workdir}")

    timeout_seconds = _token_refresher_timeout_seconds(mode)

    with tempfile.NamedTemporaryFile(
        prefix="camoufox_result_", suffix=".json", delete=False
    ) as tmp:
        output_path = Path(tmp.name)

    command = [
        python_executable,
        str(script_path),
        "--headless",
        "--workers",
        "1",
        "--email",
        owner_email,
        "--target-org-id",
        workspace.org_id,
        "--output",
        str(output_path),
        "--no-clipboard",
    ]

    logger.info(
        "Running token refresher for workspace=%s owner=%s mode=%s python=%s script=%s workdir=%s",
        workspace.org_id,
        owner_email,
        mode,
        python_executable,
        script_path,
        workdir,
    )

    try:

        def _run_refresher() -> subprocess.CompletedProcess[str]:
            child_env = os.environ.copy()
            child_env.setdefault("PYTHONIOENCODING", "utf-8")
            child_env.setdefault("PYTHONUTF8", "1")
            return subprocess.run(
                command,
                cwd=str(workdir),
                env=child_env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=timeout_seconds,
                check=False,
            )

        try:
            completed = await asyncio.to_thread(_run_refresher)
        except subprocess.TimeoutExpired as exc:
            raise TokenRefreshTimeoutError() from exc

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""

        if completed.returncode != 0:
            debug_log_path = _persist_refresher_debug_output(
                workspace_id=workspace.org_id,
                owner_email=owner_email,
                mode=mode,
                command=[str(part) for part in command],
                return_code=int(completed.returncode or 0),
                stdout=stdout,
                stderr=stderr,
            )
            logger.warning(
                "Token refresher failed for workspace=%s owner=%s mode=%s returncode=%s debug_log=%s stdout=%r stderr=%r",
                workspace.org_id,
                owner_email,
                mode,
                completed.returncode,
                debug_log_path,
                _clean_output_snippet(stdout, limit=500),
                _clean_output_snippet(stderr, limit=500),
            )
            raise _normalize_refresher_failure(
                return_code=int(completed.returncode or 0),
                stdout=stdout,
                stderr=stderr,
                debug_log_path=debug_log_path,
            )

        result = _read_result_document(output_path, owner_email)
        access_token = str(result.get("access_token") or "").strip()
        success = bool(result.get("success", True))
        error_message = str(result.get("error") or "").strip()
        debug_log_path: Path | None = None
        if not success:
            debug_log_path = _persist_refresher_debug_output(
                workspace_id=workspace.org_id,
                owner_email=owner_email,
                mode=mode,
                command=[str(part) for part in command],
                return_code=0,
                stdout=stdout,
                stderr=stderr,
            )
            raise BrowserRefreshFailedError(
                _build_detailed_failure_message(
                    error_message or "Browser refresh failed",
                    stdout=stdout,
                    stderr=stderr,
                    debug_log_path=debug_log_path,
                )
            )
        if not access_token:
            if error_message:
                debug_log_path = _persist_refresher_debug_output(
                    workspace_id=workspace.org_id,
                    owner_email=owner_email,
                    mode=mode,
                    command=[str(part) for part in command],
                    return_code=0,
                    stdout=stdout,
                    stderr=stderr,
                )
                raise BrowserRefreshFailedError(
                    _build_detailed_failure_message(
                        error_message,
                        stdout=stdout,
                        stderr=stderr,
                        debug_log_path=debug_log_path,
                    )
                )
            debug_log_path = _persist_refresher_debug_output(
                workspace_id=workspace.org_id,
                owner_email=owner_email,
                mode=mode,
                command=[str(part) for part in command],
                return_code=0,
                stdout=stdout,
                stderr=stderr,
            )
            raise BrowserRefreshFailedError(
                _build_detailed_failure_message(
                    "Browser refresh failed: refresher did not return access_token",
                    stdout=stdout,
                    stderr=stderr,
                    debug_log_path=debug_log_path,
                )
            )

        return {
            "owner_email": owner_email,
            "access_token": access_token,
            "account_id": result.get("account_id"),
            "organization_id": result.get("organization_id"),
            "success": success,
            "error": result.get("error"),
            "refreshed_at": result.get("refreshed_at"),
            "mode": result.get("mode") or mode,
        }
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            logger.warning(
                "Failed to remove token refresher output file: %s", output_path
            )


async def verify_refreshed_token_for_workspace(
    workspace: Workspace,
    refresh_result: dict[str, Any],
) -> dict[str, Any]:
    access_token = str(refresh_result.get("access_token") or "").strip()
    if not access_token:
        raise BrowserRefreshFailedError()

    try:
        claims = chatgpt_service.decode_access_token_claims(access_token)
    except (PyJWTError, ValueError, TypeError) as exc:
        raise TokenRefreshError(
            f"invalid access token: {exc}", code="invalid_access_token"
        ) from exc

    workspace_account_id = normalize_identity(str(workspace.account_id or ""))
    refreshed_account_id = normalize_identity(
        str(refresh_result.get("account_id") or "")
    )

    if (
        workspace_account_id
        and refreshed_account_id
        and refreshed_account_id != workspace_account_id
    ):
        raise TokenWorkspaceMismatchError()

    expected_account_id = workspace.account_id or refresh_result.get("account_id")
    matched_account = await _resolve_team_account_for_workspace(
        access_token,
        str(expected_account_id or "") or None,
    )
    verified_account_id = str(matched_account.get("account_id") or "").strip() or None
    verified_account_key = normalize_identity(verified_account_id)

    if workspace_account_id and verified_account_key != workspace_account_id:
        raise TokenWorkspaceMismatchError()

    token_account_id = normalize_identity(str(claims.get("sub") or ""))
    try:
        expires_at = chatgpt_service.extract_access_token_expiry(access_token)
    except (PyJWTError, ValueError, TypeError):
        expires_at = None

    return {
        **refresh_result,
        "account_id": verified_account_id,
        "claims": claims,
        "token_account_id": token_account_id,
        "expires_at": expires_at,
    }


def mark_workspace_refresh_success(
    workspace: Workspace,
    verified_result: dict[str, Any],
) -> None:
    workspace.access_token = str(verified_result["access_token"])
    refreshed_account_id = verified_result.get("account_id")
    if refreshed_account_id:
        workspace.account_id = str(refreshed_account_id)
    workspace.status = "live"
    workspace.sync_error = None
    workspace.last_token_refresh_at = utc_now()
    workspace.last_token_refresh_error = None
    workspace.token_refresh_fail_count = 0
    workspace.token_refresh_blocked = False


def mark_workspace_refresh_failure(
    workspace: Workspace,
    message: str,
    *,
    mode: str,
) -> None:
    workspace.last_token_refresh_error = message
    if mode == "auto":
        current_count = int(workspace.token_refresh_fail_count or 0) + 1
        workspace.token_refresh_fail_count = current_count
        block_threshold = max(
            1, int(os.getenv("TOKEN_AUTO_REFRESH_FAIL_THRESHOLD", "3"))
        )
        if current_count >= block_threshold:
            workspace.token_refresh_blocked = True
    workspace.status = workspace.status or "error"


def select_due_token_refresh_workspace_ids(
    session: Session, *, limit: int | None = None
) -> list[str]:
    now = utc_now()
    cutoff = now + _AUTO_REFRESH_THRESHOLD
    workspaces = (
        session.execute(select(Workspace).order_by(Workspace.org_id)).scalars().all()
    )

    due_items: list[tuple[datetime, str]] = []
    for workspace in workspaces:
        if workspace.token_refresh_blocked:
            continue
        if not workspace.access_token:
            continue
        try:
            expires_at = chatgpt_service.extract_access_token_expiry(
                workspace.access_token
            )
        except (PyJWTError, ValueError, TypeError):
            continue
        if expires_at <= cutoff:
            due_items.append((expires_at, workspace.org_id))

    due_items.sort(key=lambda item: (item[0], item[1]))
    org_ids = [org_id for _, org_id in due_items]
    return org_ids[:limit] if limit is not None else org_ids
