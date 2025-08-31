"""
JWT token handling utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import jwt
import structlog

from shared.config.settings import get_settings

from .models import TokenPayload, UserRole

logger = structlog.get_logger(__name__)


class JWTHandler:
    """JWT token creation and validation"""

    def __init__(self):
        self.settings = get_settings()
        # Use encryption key as JWT secret for now (in production, use separate secret)
        self.secret_key = self.settings.field_encryption_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 hours

    def create_access_token(
        self,
        user_id: UUID,
        username: str,
        role: UserRole,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User ID
            username: Username
            role: User role
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token
        """
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(minutes=self.access_token_expire_minutes))

        payload = {
            "user_id": str(user_id),
            "username": username,
            "role": role.value,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
        }

        logger.debug("Creating access token", user_id=user_id, username=username, expires_at=expire)

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            logger.error("Failed to create access token", error=str(e))
            raise ValueError("Failed to create access token")

    def decode_token(self, token: str) -> TokenPayload:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Validate required fields
            required_fields = ["user_id", "username", "role", "exp", "iat"]
            for field in required_fields:
                if field not in payload:
                    raise ValueError(f"Missing required field: {field}")

            # Check token type
            if payload.get("type") != "access":
                raise ValueError("Invalid token type")

            # Convert user_id back to UUID
            try:
                user_id = UUID(payload["user_id"])
            except ValueError:
                raise ValueError("Invalid user ID format")

            # Validate role
            try:
                role = UserRole(payload["role"])
            except ValueError:
                raise ValueError("Invalid role")

            return TokenPayload(
                user_id=user_id,
                username=payload["username"],
                role=role,
                exp=payload["exp"],
                iat=payload["iat"],
            )

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token", error=str(e))
            raise ValueError("Invalid token")
        except Exception as e:
            logger.error("Token decode error", error=str(e))
            raise ValueError("Token decode error")

    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token is expired without raising an exception.

        Args:
            token: JWT token string

        Returns:
            True if token is expired or invalid, False otherwise
        """
        try:
            self.decode_token(token)
            return False
        except ValueError as e:
            return "expired" in str(e).lower()

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Get the expiration time of a token.

        Args:
            token: JWT token string

        Returns:
            Expiration datetime or None if token is invalid
        """
        try:
            payload = self.decode_token(token)
            return datetime.fromtimestamp(payload.exp, tz=timezone.utc)
        except ValueError:
            return None
