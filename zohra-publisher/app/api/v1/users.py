"""
Zohra — User Management & RBAC Administration API (Part 10).

Provides:
- User creation and listing with bcrypt password hashing
- Per-site role assignment for multi-tenant isolation
- Current user profile and resolved permission claims (/me)
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import get_current_user_context, require_role
from app.core.security import hash_password
from app.db.models.operations import User, UserRole, UserSiteRole
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.schemas.operations import UserCreate, UserResponse, UserSiteRoleAssignment

router = APIRouter(prefix="/users", tags=["Users & RBAC"])


@router.get("/me", response_model=ApiResponse[dict[str, Any]])
async def get_my_profile(
    current_user: Annotated[Any, Depends(get_current_user_context)],
) -> ApiResponse[dict[str, Any]]:
    """Get active user identity, global role, and per-site permissions."""
    return ApiResponse(
        success=True,
        data={
            "user_id": current_user.user_id,
            "username": current_user.username,
            "global_role": current_user.global_role.value,
            "site_roles": {str(k): v.value for k, v in current_user.site_roles.items()},
            "is_active": current_user.is_active,
        },
    )


@router.get("", response_model=ApiResponse[list[UserResponse]])
async def list_users(
    _user: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[UserResponse]]:
    """List all registered system operators."""
    res = await db.execute(select(User).order_by(User.username))
    users = res.scalars().all()
    items = [UserResponse.model_validate(u) for u in users]
    return ApiResponse(success=True, data=items)


@router.post("", response_model=ApiResponse[UserResponse])
async def create_user(
    payload: UserCreate,
    _user: Annotated[Any, Depends(require_role(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[UserResponse]:
    """Create a new operator account."""
    # Check duplicate username
    res = await db.execute(select(User).where(User.username == payload.username))
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{payload.username}' already exists",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role.value,
        is_active=payload.is_active,
    )
    db.add(user)
    await db.flush()

    return ApiResponse(success=True, data=UserResponse.model_validate(user))


@router.post("/{user_id}/site-role", response_model=ApiResponse[dict[str, Any]])
async def assign_site_role(
    user_id: uuid.UUID,
    payload: UserSiteRoleAssignment,
    _admin: Annotated[Any, Depends(require_role(UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[dict[str, Any]]:
    """Assign or update a site-scoped role mapping for a user."""
    # Verify user exists
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Upsert site role
    res = await db.execute(
        select(UserSiteRole).where(
            UserSiteRole.user_id == user_id,
            UserSiteRole.site_id == payload.site_id,
        )
    )
    existing = res.scalar_one_or_none()
    if existing:
        existing.role = payload.role.value
    else:
        new_site_role = UserSiteRole(
            user_id=user_id,
            site_id=payload.site_id,
            role=payload.role.value,
        )
        db.add(new_site_role)

    await db.flush()

    return ApiResponse(
        success=True,
        data={
            "user_id": str(user_id),
            "site_id": str(payload.site_id),
            "role": payload.role.value,
            "message": "Site-specific role mapped successfully.",
        },
    )
