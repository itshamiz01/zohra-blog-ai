"""
Zohra — Admin authentication endpoint.

POST /api/v1/admin/login  — obtain JWT token via Basic Auth
GET  /api/v1/admin/me     — verify token and return identity
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.security import authenticate_admin, create_access_token, require_admin_token
from app.schemas.api import ApiResponse, TokenResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def admin_login(
    username: Annotated[str, Depends(authenticate_admin)],
) -> ApiResponse[TokenResponse]:
    """
    Authenticate with HTTP Basic and receive a JWT token.
    Use the token as Bearer auth for subsequent requests.
    """
    settings = get_settings()
    token = create_access_token(subject=username, extra={"role": "admin"})

    return ApiResponse(
        success=True,
        data=TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.get("/me", response_model=ApiResponse)
async def admin_me(
    token_payload: Annotated[dict, Depends(require_admin_token)],
) -> ApiResponse:
    """Return the authenticated admin identity (token validation check)."""
    return ApiResponse(
        success=True,
        data={
            "username": token_payload.get("sub"),
            "role": token_payload.get("role", "admin"),
        },
    )
