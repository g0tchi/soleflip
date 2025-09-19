"""
API Security Middleware and Utilities
Enhanced security measures for selling APIs
"""

import time
import hashlib
from typing import Dict, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Memory-based rate limiter with sliding window"""

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Dict[str, datetime] = {}

    def is_allowed(
        self,
        identifier: str,
        limit: int = 100,
        window_seconds: int = 3600,
        block_duration_minutes: int = 15
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed under rate limit

        Args:
            identifier: IP address or user identifier
            limit: Maximum requests per window
            window_seconds: Time window in seconds
            block_duration_minutes: Block duration for exceeded limits

        Returns:
            (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds

        # Check if IP is currently blocked
        if identifier in self.blocked_ips:
            unblock_time = self.blocked_ips[identifier]
            if datetime.utcnow() < unblock_time:
                retry_after = int((unblock_time - datetime.utcnow()).total_seconds())
                return False, retry_after
            else:
                # Unblock expired blocks
                del self.blocked_ips[identifier]

        # Clean old requests outside the window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]

        # Check current request count
        current_requests = len(self.requests[identifier])

        if current_requests >= limit:
            # Block the IP/user
            block_until = datetime.utcnow() + timedelta(minutes=block_duration_minutes)
            self.blocked_ips[identifier] = block_until

            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                current_requests=current_requests,
                limit=limit,
                blocked_until=block_until.isoformat()
            )

            retry_after = block_duration_minutes * 60
            return False, retry_after

        # Add current request
        self.requests[identifier].append(now)
        return True, None


class SecurityHeaders:
    """Security headers middleware"""

    @staticmethod
    def add_security_headers(response: Response) -> Response:
        """Add comprehensive security headers"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class APIKeyValidator:
    """Validate and manage API keys securely"""

    def __init__(self, valid_api_keys: Set[str]):
        # Hash API keys for secure storage
        self.valid_key_hashes = {
            hashlib.sha256(key.encode()).hexdigest() for key in valid_api_keys
        }

    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key using hash comparison"""
        if not api_key:
            return False

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return key_hash in self.valid_key_hashes


class InputSanitizer:
    """Sanitize user inputs to prevent injection attacks"""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")

        # Remove potential dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
        sanitized = value

        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized.strip()

    @staticmethod
    def validate_uuid(value: str) -> bool:
        """Validate UUID format"""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value.lower()))

    @staticmethod
    def sanitize_pricing_strategy(strategy: str) -> str:
        """Sanitize pricing strategy input"""
        allowed_strategies = {'competitive', 'premium', 'aggressive'}
        sanitized = InputSanitizer.sanitize_string(strategy, 20).lower()

        if sanitized not in allowed_strategies:
            raise ValueError(f"Invalid pricing strategy: {sanitized}")

        return sanitized


class RequestValidator:
    """Validate requests for security compliance"""

    @staticmethod
    def validate_request_size(request: Request, max_size_mb: int = 10) -> bool:
        """Validate request body size"""
        content_length = request.headers.get("content-length")
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            return size_mb <= max_size_mb
        return True

    @staticmethod
    def validate_content_type(request: Request) -> bool:
        """Validate content type for POST/PUT requests"""
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            allowed_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data"
            ]
            return any(allowed in content_type.lower() for allowed in allowed_types)
        return True


class AuditLogger:
    """Security audit logging"""

    @staticmethod
    def log_security_event(
        event_type: str,
        request: Request,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log security-related events"""
        log_data = {
            "event_type": event_type,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "method": request.method,
            "path": str(request.url.path),
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id
        }

        if additional_data:
            log_data.update(additional_data)

        logger.info("Security audit event", **log_data)


# Global instances
rate_limiter = RateLimiter()
input_sanitizer = InputSanitizer()
request_validator = RequestValidator()
audit_logger = AuditLogger()


# Security Middleware Function
async def security_middleware(request: Request, call_next: Callable) -> Response:
    """Comprehensive security middleware"""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"

    try:
        # Request size validation
        if not request_validator.validate_request_size(request):
            audit_logger.log_security_event(
                "oversized_request",
                request,
                additional_data={"content_length": request.headers.get("content-length")}
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request size exceeds limit"
            )

        # Content type validation
        if not request_validator.validate_content_type(request):
            audit_logger.log_security_event("invalid_content_type", request)
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported content type"
            )

        # Rate limiting for selling endpoints
        if "/selling/" in str(request.url.path):
            is_allowed, retry_after = rate_limiter.is_allowed(
                identifier=client_ip,
                limit=200,  # 200 requests per hour for selling operations
                window_seconds=3600
            )

            if not is_allowed:
                audit_logger.log_security_event("rate_limit_exceeded", request)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)} if retry_after else None
                )

        # Process request
        response = await call_next(request)

        # Add security headers
        response = SecurityHeaders.add_security_headers(response)

        # Log successful request
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        return response

    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected errors
        audit_logger.log_security_event(
            "unexpected_error",
            request,
            additional_data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Security Dependency Functions for FastAPI
def get_client_ip(request: Request) -> str:
    """Extract client IP address safely"""
    # Check for forwarded headers (reverse proxy)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take first IP if multiple
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection
    return request.client.host if request.client else "unknown"


def validate_user_permissions(required_permissions: Set[str]):
    """Dependency to validate user permissions"""
    def permission_checker(user = None):  # User object from auth dependency
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # Check user permissions (implement based on your user model)
        user_permissions = getattr(user, 'permissions', set())
        if not required_permissions.issubset(user_permissions):
            audit_logger.log_security_event(
                "insufficient_permissions",
                request=None,  # Would need to be passed in
                user_id=str(user.id),
                additional_data={
                    "required": list(required_permissions),
                    "user_permissions": list(user_permissions)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return user

    return permission_checker