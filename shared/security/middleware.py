"""
Security Middleware Collection
Production-ready security middleware for FastAPI applications
"""

from typing import Callable, Dict, Any, Optional, List
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio


logger = structlog.get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    def __init__(
        self,
        app: ASGIApp,
        frame_options: str = "DENY",
        content_type_options: str = "nosniff",
        xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: Optional[str] = None,
        csp: Optional[str] = None,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
    ):
        super().__init__(app)
        self.frame_options = frame_options
        self.content_type_options = content_type_options
        self.xss_protection = xss_protection
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy
        self.csp = csp
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Add security headers
        response.headers["X-Frame-Options"] = self.frame_options
        response.headers["X-Content-Type-Options"] = self.content_type_options
        response.headers["X-XSS-Protection"] = self.xss_protection
        response.headers["Referrer-Policy"] = self.referrer_policy

        # Add HSTS header for HTTPS
        if request.url.scheme == "https":
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # Optional headers
        if self.permissions_policy:
            response.headers["Permissions-Policy"] = self.permissions_policy

        if self.csp:
            response.headers["Content-Security-Policy"] = self.csp

        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with sliding window algorithm"""

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 100,
        burst_size: int = 20,
        whitelist_ips: Optional[List[str]] = None,
        blacklist_ips: Optional[List[str]] = None,
        rate_limit_by: str = "ip",  # "ip" or "user"
        cleanup_interval: int = 300,  # seconds
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.whitelist_ips = set(whitelist_ips or [])
        self.blacklist_ips = set(blacklist_ips or [])
        self.rate_limit_by = rate_limit_by
        self.cleanup_interval = cleanup_interval

        # Sliding window storage: {identifier: deque(timestamps)}
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque())
        self.last_cleanup = time.time()

    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        if self.rate_limit_by == "user":
            # Extract user ID from headers/auth (placeholder)
            user_id = request.headers.get("X-User-ID")
            if user_id:
                return f"user:{user_id}"

        # Fallback to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _cleanup_old_entries(self):
        """Remove old entries from request history"""
        current_time = time.time()
        cutoff_time = current_time - 60  # Remove entries older than 1 minute

        for identifier, history in list(self.request_history.items()):
            # Remove old timestamps
            while history and history[0] < cutoff_time:
                history.popleft()

            # Remove empty histories
            if not history:
                del self.request_history[identifier]

        self.last_cleanup = current_time

    def _is_rate_limited(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """Check if client is rate limited"""
        current_time = time.time()
        history = self.request_history[identifier]

        # Remove old entries
        cutoff_time = current_time - 60
        while history and history[0] < cutoff_time:
            history.popleft()

        # Check burst limit (requests in last 10 seconds)
        burst_cutoff = current_time - 10
        burst_count = sum(1 for ts in history if ts > burst_cutoff)

        if burst_count >= self.burst_size:
            return True, {
                "reason": "burst_limit_exceeded",
                "limit": self.burst_size,
                "window": "10 seconds",
                "current": burst_count,
            }

        # Check per-minute limit
        if len(history) >= self.requests_per_minute:
            return True, {
                "reason": "rate_limit_exceeded",
                "limit": self.requests_per_minute,
                "window": "1 minute",
                "current": len(history),
            }

        return False, {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_id = self._get_client_identifier(request)

        # Check blacklist
        if client_id in self.blacklist_ips:
            logger.warning("Blocked request from blacklisted IP", client_ip=client_id)
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "IP_BLACKLISTED", "message": "Access denied"}},
            )

        # Skip rate limiting for whitelisted IPs
        if client_id not in self.whitelist_ips:
            # Periodic cleanup
            if time.time() - self.last_cleanup > self.cleanup_interval:
                self._cleanup_old_entries()

            # Check rate limit
            is_limited, limit_info = self._is_rate_limited(client_id)
            if is_limited:
                logger.warning(
                    "Rate limit exceeded", client_id=client_id, path=request.url.path, **limit_info
                )

                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests",
                            "details": limit_info,
                        }
                    },
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": str(
                            max(0, self.requests_per_minute - limit_info.get("current", 0))
                        ),
                        "X-RateLimit-Reset": str(int(time.time() + 60)),
                    },
                )

        # Record request
        self.request_history[client_id].append(time.time())

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        if client_id not in self.whitelist_ips:
            current_count = len(self.request_history[client_id])
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, self.requests_per_minute - current_count)
            )
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS attacks"""

    def __init__(self, app: ASGIApp, max_size: int = 50 * 1024 * 1024):  # 50MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                if int(content_length) > self.max_size:
                    logger.warning(
                        "Request size limit exceeded",
                        content_length=content_length,
                        max_size=self.max_size,
                        path=request.url.path,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "REQUEST_TOO_LARGE",
                                "message": f"Request body too large. Maximum size: {self.max_size} bytes",
                            }
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware using double-submit cookie pattern"""

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        safe_methods: Optional[List[str]] = None,
        exempt_paths: Optional[List[str]] = None,
        token_header: str = "X-CSRF-Token",
        cookie_name: str = "csrf_token",
        cookie_httponly: bool = False,
        cookie_secure: bool = True,
        cookie_samesite: str = "strict",
    ):
        super().__init__(app)
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.safe_methods = set(safe_methods or ["GET", "HEAD", "OPTIONS", "TRACE"])
        self.exempt_paths = set(exempt_paths or ["/health", "/docs", "/openapi.json"])
        self.token_header = token_header
        self.cookie_name = cookie_name
        self.cookie_httponly = cookie_httponly
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite

    def _generate_csrf_token(self) -> str:
        """Generate a new CSRF token"""
        timestamp = str(int(time.time()))
        random_part = secrets.token_urlsafe(32)
        message = f"{timestamp}:{random_part}"

        # Create HMAC signature
        import hmac

        signature = hmac.new(self.secret_key, message.encode(), hashlib.sha256).hexdigest()

        return f"{message}:{signature}"

    def _validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token"""
        try:
            parts = token.split(":")
            if len(parts) != 3:
                return False

            timestamp, random_part, signature = parts
            message = f"{timestamp}:{random_part}"

            # Verify signature
            import hmac

            expected_signature = hmac.new(
                self.secret_key, message.encode(), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_signature):
                return False

            # Check token age (valid for 1 hour)
            token_age = time.time() - int(timestamp)
            return token_age < 3600

        except (ValueError, TypeError):
            return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF protection for safe methods and exempt paths
        if request.method in self.safe_methods or request.url.path in self.exempt_paths:
            response = await call_next(request)
        else:
            # Check for CSRF token
            token_from_header = request.headers.get(self.token_header)
            token_from_cookie = request.cookies.get(self.cookie_name)

            # Both tokens must be present and match
            if (
                not token_from_header
                or not token_from_cookie
                or token_from_header != token_from_cookie
                or not self._validate_csrf_token(token_from_header)
            ):

                logger.warning(
                    "CSRF token validation failed",
                    path=request.url.path,
                    method=request.method,
                    has_header_token=bool(token_from_header),
                    has_cookie_token=bool(token_from_cookie),
                    tokens_match=(
                        token_from_header == token_from_cookie
                        if token_from_header and token_from_cookie
                        else False
                    ),
                )

                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "CSRF_TOKEN_INVALID",
                            "message": "CSRF token validation failed",
                        }
                    },
                )

            response = await call_next(request)

        # Always set/refresh CSRF token in cookie
        csrf_token = self._generate_csrf_token()
        response.set_cookie(
            self.cookie_name,
            csrf_token,
            httponly=self.cookie_httponly,
            secure=self.cookie_secure,
            samesite=self.cookie_samesite,
            max_age=3600,  # 1 hour
        )

        return response


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """Validate Host header against allowed hosts"""

    def __init__(self, app: ASGIApp, allowed_hosts: List[str]):
        super().__init__(app)
        self.allowed_hosts = set(allowed_hosts)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        host = request.headers.get("host", "").lower()

        # Remove port from host if present
        host_without_port = host.split(":")[0]

        # Check if host is allowed (support wildcards)
        allowed = False
        for allowed_host in self.allowed_hosts:
            if allowed_host == "*":
                allowed = True
                break
            elif allowed_host.startswith("*."):
                # Wildcard subdomain
                domain = allowed_host[2:]
                if host_without_port == domain or host_without_port.endswith(f".{domain}"):
                    allowed = True
                    break
            elif host_without_port == allowed_host:
                allowed = True
                break

        if not allowed:
            logger.warning("Invalid Host header", host=host, allowed_hosts=list(self.allowed_hosts))
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "INVALID_HOST", "message": "Invalid Host header"}},
            )

        return await call_next(request)


# Utility function to add all security middleware
def add_security_middleware(app, settings):
    """Add all security middleware to FastAPI app"""

    # Request size limiting
    app.add_middleware(RequestSizeLimitMiddleware, max_size=settings.security.max_request_size)

    # Rate limiting (if enabled)
    if settings.security.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.security.rate_limit_requests,
            burst_size=settings.security.rate_limit_requests // 5,  # 20% of per-minute limit
        )

    # CSRF protection (only in production)
    if settings.is_production():
        app.add_middleware(
            CSRFProtectionMiddleware, secret_key=settings.security.secret_key, cookie_secure=True
        )

    # Trusted host validation
    if settings.security.allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.security.allowed_hosts)

    # Security headers
    csp_policy = None
    if settings.is_production():
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

    app.add_middleware(
        SecurityHeadersMiddleware,
        csp=csp_policy,
        permissions_policy=(
            (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            )
            if settings.is_production()
            else None
        ),
    )

    logger.info(
        "Security middleware configured",
        rate_limiting=settings.security.rate_limit_enabled,
        csrf_protection=settings.is_production(),
        trusted_hosts=settings.security.allowed_hosts != ["*"],
        max_request_size=settings.security.max_request_size,
    )
