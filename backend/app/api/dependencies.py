"""
KerjaCerdas — API Dependencies
================================
FastAPI dependencies for authentication, database sessions, and role checks.

Convention: every secured endpoint must depend on get_current_user (or a
role-scoped wrapper built on top of it) rather than reading the bearer token
itself.
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.api.database import get_session
from backend.app.api.services.auth_service import decode_access_token
from backend.app.db.models import User

logger = logging.getLogger(__name__)

# Production frontend will pass the token in Authorization: Bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session),
) -> User:
    """
    Validate JWT token and return the current User object.

    Raises 401 Unauthorized if token is missing, invalid, or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Query the user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(f"Valid token but user {user_id} not found in DB")
        raise credentials_exception

    if not user.is_active:
        logger.warning(f"Inactive user {user_id} attempted access")
        raise HTTPException(status_code=400, detail="Inactive user account")

    return user


async def require_employer(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the user is an employer."""
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Employer access required"
        )
    return current_user


async def require_seeker(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the user is a job seeker."""
    if current_user.role != "seeker":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seeker access required")
    return current_user


oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_session),
) -> User | None:
    """Like get_current_user but returns None instead of raising 401.

    Used by endpoints that serve both authenticated and anonymous users
    (e.g. /events/track where anonymous events are still valuable).
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if not payload:
            return None
        user_id: str | None = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:  # noqa: BLE001
        return None


def is_admin_email(email: str | None) -> bool:
    """Whether this address may use the admin surface right now.

    Read at call time, never cached: ADMIN_EMAILS / ADMIN_ROUTES_ENABLED can be
    changed in a deployment's secrets, and a token minted before that change
    must not carry stale admin rights. The login response only *advertises* the
    flag so the UI can show the entry point — every admin route re-checks it.
    """
    from backend.app.config.settings import settings

    if not settings.admin_routes_enabled or not email:
        return False
    allowed = {e.strip().lower() for e in settings.admin_emails if e.strip()}
    return email.lower() in allowed


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Admin = authenticated account whose email is listed in ADMIN_EMAILS.

    Also requires ADMIN_ROUTES_ENABLED, so a deployment that never configured
    admins exposes no cross-user admin surface at all.
    """
    if not is_admin_email(current_user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
