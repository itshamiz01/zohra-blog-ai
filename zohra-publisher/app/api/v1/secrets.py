"""
Zohra — Encrypted Credential & Secret Management API (Part 10).

Provides:
- Storing encrypted site credentials with authenticated encryption
- Listing secret metadata (version, status, rotation timestamp) with ZERO plaintext leakage
- Rotating secrets safely
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_role
from app.db.models.operations import UserRole
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.schemas.operations import (
    SecretCreateRequest,
    SecretMetadataResponse,
)
from app.services.secrets import EncryptedDatabaseSecretProvider

router = APIRouter(prefix="/secrets", tags=["Secret Management"])


@router.get("", response_model=ApiResponse[list[SecretMetadataResponse]])
async def list_secrets(
    _user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    site_id: uuid.UUID | None = None,
) -> ApiResponse[list[SecretMetadataResponse]]:
    """
    List stored credentials metadata.
    Never exposes plaintext secrets or passwords.
    """
    provider = EncryptedDatabaseSecretProvider(db)
    meta = await provider.list_secret_metadata(site_id=site_id)
    items = [SecretMetadataResponse(**m) for m in meta]
    return ApiResponse(success=True, data=items)


@router.post("", response_model=ApiResponse[dict[str, Any]])
async def store_secret(
    payload: SecretCreateRequest,
    _user: Annotated[Any, Depends(require_role(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Store encrypted credential. Plaintext is encrypted immediately before persistence."""
    provider = EncryptedDatabaseSecretProvider(db)
    version = await provider.set_secret(
        key_name=payload.key_name,
        value=payload.value,
        site_id=payload.site_id,
    )
    return ApiResponse(
        success=True,
        data={
            "key_name": payload.key_name,
            "version": version,
            "status": "STORED_AND_ENCRYPTED",
            "message": "Credential encrypted and stored securely.",
        },
    )


@router.post("/rotate", response_model=ApiResponse[dict[str, Any]])
async def rotate_secret(
    payload: SecretCreateRequest,
    _user: Annotated[Any, Depends(require_role(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Rotate an existing credential to a new encrypted version."""
    provider = EncryptedDatabaseSecretProvider(db)
    version = await provider.rotate_secret(
        key_name=payload.key_name,
        new_value=payload.value,
        site_id=payload.site_id,
    )
    return ApiResponse(
        success=True,
        data={
            "key_name": payload.key_name,
            "version": version,
            "status": "ROTATED",
            "message": "Credential rotated to new active version.",
        },
    )
