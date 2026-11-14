"""
Zohra — Security utilities.

Provides:
  - password hashing / verification (bcrypt)
  - JWT token creation / validation
  - admin authentication dependency for FastAPI
  - request-ID middleware

Design allows future replacement with OAuth2 / SSO without
changing the rest of the application.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from jose import JWTError, jwt

from app.core.config import get_settings

# ── Password Hashing ─────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT Tokens ───────────────────────────────────────────────────


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


# ── Request ID Middleware ────────────────────────────────────────

REQUEST_ID_HEADER = "X-Request-ID"


def get_request_id(request: Request) -> str:
    """Extract or generate a request correlation ID."""
    return request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))


# ── FastAPI Auth Dependencies ────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)
_basic_scheme = HTTPBasic(auto_error=False)


async def require_admin_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> dict[str, Any]:
    """
    Admin gate — AUTHENTICATION DISABLED at the owner's explicit request
    (2026-11-14): the owner is the only user and asked for the username /
    password login to be removed, so every request is treated as the
    built-in admin (sub="admin" -> SUPER_ADMIN in rbac). A valid Bearer
    token, when one is presented, is still honoured as before.
    To re-enable login, restore the strict version of this function from
    git history (see the commit that introduced this note).
    """
    if credentials is not None:
        try:
            return decode_access_token(credentials.credentials)
        except JWTError:
            pass
    return {"sub": "admin", "role": "super_admin"}


async def authenticate_admin(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic_scheme)],
) -> str:
    """
    Dependency for login endpoint — verifies admin username + password.
    Returns the username on success.
    """
    settings = get_settings()
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    if credentials.username != settings.ADMIN_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not verify_password(credentials.password, settings.ADMIN_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
