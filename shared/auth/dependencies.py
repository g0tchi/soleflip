"""
FastAPI authentication dependencies.
"""

from typing import Optional

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db_session
from shared.repositories.base_repository import BaseRepository

from .jwt_handler import JWTHandler
from .models import TokenPayload, User, UserRole

logger = structlog.get_logger(__name__)

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Authentication error exception"""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Authorization error exception"""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Extract and validate current user from JWT token.

    Args:
        credentials: HTTP Authorization header with Bearer token
        db: Database session

    Returns:
        Current authenticated user

    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    if not credentials:
        logger.warning("No authorization header provided")
        raise AuthenticationError("No authorization header provided")

    token = credentials.credentials
    jwt_handler = JWTHandler()

    try:
        # Decode and validate token
        token_payload = jwt_handler.decode_token(token)

        # Get user from database
        user_repo = BaseRepository(User, db)
        user = await user_repo.get_by_id(token_payload.user_id)

        if not user:
            logger.warning("User not found", user_id=token_payload.user_id)
            raise AuthenticationError("User not found")

        if not user.is_active:
            logger.warning("User account is inactive", user_id=user.id)
            raise AuthenticationError("User account is inactive")

        logger.debug("User authenticated successfully", user_id=user.id, username=user.username)
        return user

    except ValueError as e:
        logger.warning("Token validation failed", error=str(e))
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise AuthenticationError("Authentication failed")


async def get_current_user(user: User = Depends(get_current_user_from_token)) -> User:
    """
    Get current authenticated user (main dependency).

    Args:
        user: User from token validation

    Returns:
        Current authenticated user
    """
    return user


async def require_authenticated_user(user: User = Depends(get_current_user)) -> User:
    """
    Require any authenticated user.

    Args:
        user: Current user

    Returns:
        Current authenticated user
    """
    return user


async def require_admin_role(user: User = Depends(get_current_user)) -> User:
    """
    Require admin role for endpoint access.

    Args:
        user: Current user

    Returns:
        Current user if admin

    Raises:
        AuthorizationError: If user is not admin
    """
    if user.role != UserRole.ADMIN:
        logger.warning("Admin access denied", user_id=user.id, role=user.role.value)
        raise AuthorizationError("Admin access required")

    return user


async def require_user_or_admin_role(user: User = Depends(get_current_user)) -> User:
    """
    Require user or admin role (excludes readonly).

    Args:
        user: Current user

    Returns:
        Current user if user or admin

    Raises:
        AuthorizationError: If user is readonly
    """
    if user.role == UserRole.READONLY:
        logger.warning("Write access denied for readonly user", user_id=user.id)
        raise AuthorizationError("Write access not permitted for readonly users")

    return user


# Optional authentication (for public endpoints that can show more data if authenticated)
async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise (no error).

    Args:
        credentials: HTTP Authorization header with Bearer token
        db: Database session

    Returns:
        Current user if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return await get_current_user_from_token(credentials, db)
    except (AuthenticationError, AuthorizationError):
        # Silently return None for optional authentication
        return None
