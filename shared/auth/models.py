"""
Authentication models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from shared.database.models import Base
from shared.database.utils import IS_POSTGRES


class UserRole(str, Enum):
    """User roles enum"""

    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class User(Base):
    """User model for authentication"""

    __tablename__ = "users"
    __table_args__ = {"schema": "auth"} if IS_POSTGRES else None

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.USER)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# Pydantic models for API
class UserCreate(BaseModel):
    """User creation request"""

    email: str = Field(..., description="User email")
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    password: str = Field(..., min_length=8, description="Password")
    role: UserRole = Field(UserRole.USER, description="User role")


class UserResponse(BaseModel):
    """User response model"""

    id: UUID
    email: str
    username: str
    role: UserRole
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Login request"""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class AuthToken(BaseModel):
    """Authentication token response"""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="User information")


class TokenPayload(BaseModel):
    """JWT token payload"""

    user_id: UUID = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    role: UserRole = Field(..., description="User role")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
