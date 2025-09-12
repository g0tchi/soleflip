"""
Authentication API endpoints.
"""

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.api.responses import create_success_response
from shared.auth.dependencies import get_current_user, require_admin_role
from shared.auth.jwt_handler import JWTHandler
from shared.auth.models import AuthToken, LoginRequest, User, UserCreate, UserResponse
from shared.auth.password_hasher import PasswordHasher
from shared.database.connection import get_db_session
from shared.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=AuthToken)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    """
    Authenticate user and return access token.

    Args:
        login_data: Username/email and password
        db: Database session

    Returns:
        Access token and user information
    """
    logger.info("Login attempt", username=login_data.username)

    try:
        # Find user by username or email
        user_repo = BaseRepository(User, db)

        # Try to find by username first, then email
        user = await user_repo.find_one(username=login_data.username)
        if not user:
            user = await user_repo.find_one(email=login_data.username)

        if not user:
            logger.warning("User not found", username=login_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
            )

        # Check if user is active
        if not user.is_active:
            logger.warning("Inactive user login attempt", user_id=user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is inactive"
            )

        # Verify password
        password_hasher = PasswordHasher()
        if not password_hasher.verify_password(login_data.password, user.hashed_password):
            logger.warning("Invalid password", user_id=user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
            )

        # Update last login
        await user_repo.update(user.id, last_login=datetime.now(timezone.utc))

        # Create access token
        jwt_handler = JWTHandler()
        access_token = jwt_handler.create_access_token(
            user_id=user.id, username=user.username, role=user.role
        )

        # Create user response
        user_response = UserResponse.model_validate(user)

        logger.info("Login successful", user_id=user.id, username=user.username)

        return AuthToken(
            access_token=access_token,
            token_type="bearer",
            expires_in=jwt_handler.access_token_expire_minutes * 60,  # Convert to seconds
            user=user_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        )


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    current_user: User = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register a new user (admin only).

    Args:
        user_data: User registration data
        current_user: Current admin user
        db: Database session

    Returns:
        Created user information
    """
    logger.info("User registration attempt", email=user_data.email, username=user_data.username)

    try:
        user_repo = BaseRepository(User, db)

        # Check if user already exists
        if await user_repo.find_one(email=user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
            )

        if await user_repo.find_one(username=user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

        # Hash password
        password_hasher = PasswordHasher()
        hashed_password = password_hasher.hash_password(user_data.password)

        # Create user
        user = await user_repo.create(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            role=user_data.role,
            is_active=True,
        )

        logger.info("User registered successfully", user_id=user.id, username=user.username)

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Registration error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Registration failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user information
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user and blacklist the JWT token.
    
    Args:
        request: FastAPI request object (to extract token)
        current_user: Current authenticated user

    Returns:
        Success message
    """
    # Extract JWT token from Authorization header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Get token expiration from JWT handler
        try:
            from shared.auth.jwt_handler import get_jwt_handler
            from shared.auth.token_blacklist import blacklist_token
            import jwt
            
            # Decode token to get expiration (without verification)
            jwt_handler = get_jwt_handler()
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            exp_timestamp = unverified_payload.get("exp")
            
            if exp_timestamp:
                # Add token to blacklist
                await blacklist_token(token, exp_timestamp)
                logger.info(
                    "User logout with token blacklisted", 
                    user_id=current_user.id, 
                    username=current_user.username,
                    token_prefix=token[:20] + "..."
                )
            else:
                logger.warning("Token has no expiration, cannot blacklist properly")
        
        except Exception as e:
            logger.error(f"Failed to blacklist token during logout: {e}")
    else:
        logger.info("User logout without valid token", user_id=current_user.id, username=current_user.username)

    return create_success_response(
        message="Successfully logged out", data={"username": current_user.username}
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin_role), db: AsyncSession = Depends(get_db_session)
):
    """
    List all users (admin only).

    Args:
        current_user: Current admin user
        db: Database session

    Returns:
        List of all users
    """
    try:
        user_repo = BaseRepository(User, db)
        users = await user_repo.get_all(order_by="created_at")

        return [UserResponse.model_validate(user) for user in users]

    except Exception as e:
        logger.error("List users error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve users"
        )


@router.patch("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Activate a user account (admin only).

    Args:
        user_id: User ID to activate
        current_user: Current admin user
        db: Database session

    Returns:
        Success message
    """
    try:
        user_repo = BaseRepository(User, db)

        updated_user = await user_repo.update(user_id, is_active=True)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        logger.info("User activated", user_id=user_id, admin_user=current_user.username)

        return create_success_response(
            message="User activated successfully", data={"user_id": user_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("User activation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to activate user"
        )


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_admin_role),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Deactivate a user account (admin only).

    Args:
        user_id: User ID to deactivate
        current_user: Current admin user
        db: Database session

    Returns:
        Success message
    """
    try:
        # Prevent admin from deactivating themselves
        if str(current_user.id) == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account"
            )

        user_repo = BaseRepository(User, db)

        updated_user = await user_repo.update(user_id, is_active=False)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        logger.info("User deactivated", user_id=user_id, admin_user=current_user.username)

        return create_success_response(
            message="User deactivated successfully", data={"user_id": user_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("User deactivation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to deactivate user"
        )
