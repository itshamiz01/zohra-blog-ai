"""
Zohra — Role-Based Access Control (RBAC) & Site Authorization.

Provides:
- Hierarchy ranking for UserRole (SUPER_ADMIN, ADMIN, EDITOR, ANALYST, VIEWER)
- Global role requirement dependencies for FastAPI endpoints
- Per-site role authorization dependencies
- Programmatic permission validation helpers
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_token
from app.db.models.operations import User, UserRole, UserSiteRole
from app.db.session import get_db

ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.VIEWER: 1,
    UserRole.ANALYST: 2,
    UserRole.EDITOR: 3,
    UserRole.ADMIN: 4,
    UserRole.SUPER_ADMIN: 5,
}


def is_role_sufficient(user_role: str | UserRole, required_role: UserRole) -> bool:
    """Check if user_role satisfies the minimum required_role in the hierarchy."""
    if isinstance(user_role, UserRole):
        user_r = user_role
    else:
        try:
            user_r = UserRole(user_role)
        except ValueError:
            return False
    return ROLE_HIERARCHY.get(user_r, 0) >= ROLE_HIERARCHY.get(required_role, 0)


class AuthenticatedUserContext:
    """Resolved user identity and permissions for the active request."""

    def __init__(
        self,
        user_id: str,
        username: str,
        global_role: UserRole,
        site_roles: dict[uuid.UUID, UserRole] | None = None,
        is_active: bool = True,
    ):
        self.user_id = user_id
        self.username = username
        self.global_role = global_role
        self.site_roles = site_roles or {}
        self.is_active = is_active

    def can_access_globally(self, required_role: UserRole) -> bool:
        """Verify global role sufficiency."""
        if not self.is_active:
            return False
        return is_role_sufficient(self.global_role, required_role)

    def can_access_site(self, site_id: uuid.UUID | str, required_role: UserRole) -> bool:
        """
        Verify site access.
        SUPER_ADMIN can access any site.
        Global ADMIN can access any site.
        Otherwise checks site-specific assignment in user_site_roles.
        """
        if not self.is_active:
            return False
        # Global high privilege automatically grants site access
        if self.global_role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            return is_role_sufficient(self.global_role, required_role)

        sid = uuid.UUID(str(site_id)) if not isinstance(site_id, uuid.UUID) else site_id
        site_role = self.site_roles.get(sid)
        if site_role is not None and is_role_sufficient(site_role, required_role):
            return True

        # Fallback to global role if sufficient (e.g. global EDITOR has editor rights across sites)
        return is_role_sufficient(self.global_role, required_role)


async def get_current_user_context(
    token_payload: Annotated[dict[str, Any], Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthenticatedUserContext:
    """
    Resolve active user context from JWT token payload.
    Supports backward compatibility with the default admin token ("sub": "admin").
    """
    sub = token_payload.get("sub", "")
    role_claim = token_payload.get("role")

    # Check if sub is a valid UUID representing a stored User in DB
    user_uuid: uuid.UUID | None = None
    try:
        user_uuid = uuid.UUID(sub)
    except (ValueError, TypeError):
        pass

    if user_uuid:
        query = select(User).where(User.id == user_uuid)
        res = await db.execute(query)
        db_user = res.scalar_one_or_none()
        if db_user:
            if not db_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is deactivated",
                )
            # Fetch site roles
            site_query = select(UserSiteRole).where(UserSiteRole.user_id == db_user.id)
            site_res = await db.execute(site_query)
            site_mappings = {sr.site_id: UserRole(sr.role) for sr in site_res.scalars().all()}

            return AuthenticatedUserContext(
                user_id=str(db_user.id),
                username=db_user.username,
                global_role=UserRole(db_user.role),
                site_roles=site_mappings,
                is_active=db_user.is_active,
            )

    # Legacy admin or system token with sub="admin" or direct claims
    assigned_role = UserRole.SUPER_ADMIN
    if role_claim:
        try:
            assigned_role = UserRole(role_claim)
        except ValueError:
            if sub == "admin" or str(role_claim).lower() in ("admin", "super_admin"):
                assigned_role = UserRole.SUPER_ADMIN
            else:
                assigned_role = UserRole.VIEWER
    elif sub != "admin":
        assigned_role = UserRole.VIEWER

    return AuthenticatedUserContext(
        user_id=sub or "system_admin",
        username=sub or "admin",
        global_role=assigned_role,
        site_roles={},
        is_active=True,
    )


def require_role(required_role: UserRole) -> Callable[..., Any]:
    """FastAPI dependency factory enforcing a minimum global role."""
    async def _role_checker(
        current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user_context)],
    ) -> AuthenticatedUserContext:
        if not current_user.can_access_globally(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires minimum global role '{required_role.value}'",
            )
        return current_user

    return _role_checker


def require_site_role(required_role: UserRole) -> Callable[..., Any]:
    """
    FastAPI dependency factory enforcing site-scoped permissions.
    Extracts site_id from path parameters or query parameters.
    """
    async def _site_role_checker(
        request: Request,
        current_user: Annotated[AuthenticatedUserContext, Depends(get_current_user_context)],
    ) -> AuthenticatedUserContext:
        site_id_str = request.path_params.get("site_id") or request.query_params.get("site_id")
        if not site_id_str:
            # If no site_id in request, check global permission
            if not current_user.can_access_globally(required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Operation requires role '{required_role.value}'",
                )
            return current_user

        try:
            site_uuid = uuid.UUID(str(site_id_str))
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid site_id UUID format",
            ) from err

        if not current_user.can_access_site(site_uuid, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for site '{site_id_str}'. Requires '{required_role.value}'.",
            )
        return current_user

    return _site_role_checker
