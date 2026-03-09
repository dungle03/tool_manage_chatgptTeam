"""Authentication dependencies for API endpoints."""

import os

from fastapi import Header, HTTPException


async def verify_admin_token(
    authorization: str = Header(default=""),
) -> str:
    """Verify admin Bearer token from Authorization header.

    In development (ADMIN_TOKEN not set), authentication is bypassed.
    In production, requires: Authorization: Bearer <token>
    """
    expected = os.getenv("ADMIN_TOKEN")

    # Development mode: skip auth if ADMIN_TOKEN not configured
    if not expected:
        return "dev-mode"

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid token")

    return token
