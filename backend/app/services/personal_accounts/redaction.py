from typing import Any

SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "authorization",
    "code_verifier",
}


def redact_sensitive(value: Any) -> Any:
    """Recursively redact token-bearing values before logs/errors."""
    if isinstance(value, dict):
        return {
            key: (
                "***REDACTED***"
                if key.lower() in SENSITIVE_KEYS
                else redact_sensitive(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def compact_error_message(value: Any, *, limit: int = 240) -> str:
    if value is None:
        return ""
    text = str(redact_sensitive(value)).strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."
