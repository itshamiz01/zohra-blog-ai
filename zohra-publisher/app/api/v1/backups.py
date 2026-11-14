"""
Zohra — Backup & Disaster Recovery Administration API (Part 10).

Provides:
- Listing created backup artifacts and manifests
- Triggering on-demand encrypted database backups
- Cryptographic checksum and decryption verification
- Isolated sandbox database restore testing
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_role
from app.db.models.operations import UserRole
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.schemas.operations import (
    BackupItemResponse,
    BackupRestoreTestResponse,
    BackupVerifyResponse,
)
from app.services.backup import BackupManager, BackupVerificationError

router = APIRouter(prefix="/backups", tags=["Backups & Recovery"])


@router.get("", response_model=ApiResponse[list[BackupItemResponse]])
async def list_backups(
    _user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[BackupItemResponse]]:
    """List all available system backups."""
    mgr = BackupManager(db)
    items = mgr.list_backups()
    return ApiResponse(
        success=True,
        data=[BackupItemResponse(**i) for i in items],
    )


@router.post("", response_model=ApiResponse[BackupItemResponse])
async def trigger_backup(
    _user: Annotated[Any, Depends(require_role(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    encrypt: bool = True,
) -> ApiResponse[BackupItemResponse]:
    """Create a verified, encrypted database backup snapshot."""
    mgr = BackupManager(db)
    manifest = await mgr.create_backup(encrypt=encrypt)
    return ApiResponse(success=True, data=BackupItemResponse(**manifest))


@router.post("/{backup_filename}/verify", response_model=ApiResponse[BackupVerifyResponse])
async def verify_backup(
    backup_filename: str,
    _user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[BackupVerifyResponse]:
    """Verify backup integrity: file existence, size, SHA-256 checksum, and decryption."""
    mgr = BackupManager(db)
    try:
        res = mgr.verify_backup(backup_filename)
        return ApiResponse(success=True, data=BackupVerifyResponse(**res))
    except BackupVerificationError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post("/{backup_filename}/test-restore", response_model=ApiResponse[BackupRestoreTestResponse])
async def test_restore_backup(
    backup_filename: str,
    _user: Annotated[Any, Depends(require_role(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[BackupRestoreTestResponse]:
    """Test restoring the backup artifact into an isolated temporary database sandbox."""
    mgr = BackupManager(db)
    try:
        success = mgr.test_restore_in_sandbox(backup_filename)
        from datetime import UTC, datetime
        return ApiResponse(
            success=True,
            data=BackupRestoreTestResponse(
                backup_name=backup_filename,
                sandbox_restore_success=success,
                tested_at=datetime.now(UTC).isoformat(),
            ),
        )
    except BackupVerificationError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
