"""
ETag Middleware for Conditional Requests
Implements HTTP ETags for efficient caching and bandwidth reduction
"""

import hashlib
import time
from typing import Optional
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class ETagMiddleware(BaseHTTPMiddleware):
    """
    ETag middleware implementing conditional requests:
    - Generates ETags based on response content
    - Handles If-None-Match headers
    - Returns 304 Not Modified when appropriate
    - Reduces bandwidth for unchanged responses
    """
    
    def __init__(self, app, weak_etags: bool = True, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.weak_etags = weak_etags
        self.exclude_paths = exclude_paths or [
            "/health", "/metrics", "/docs", "/openapi.json",
            "/health/ready", "/health/live"
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add ETag support"""
        
        # Skip ETag for excluded paths and non-GET requests  
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            logger.debug("ETag skipped - excluded path", path=request.url.path)
            return await call_next(request)
            
        if request.method not in ["GET", "HEAD"]:
            logger.debug("ETag skipped - method not supported", method=request.method)
            return await call_next(request)
        
        # Get client's ETag from If-None-Match header
        client_etag = request.headers.get("if-none-match")
        
        # Process the request
        start_time = time.time()
        response = await call_next(request)
        
        # Only add ETags for successful responses
        if response.status_code != 200:
            return response
        
        # Get response body to generate ETag
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        # Generate ETag from content
        content_hash = hashlib.md5(response_body).hexdigest()[:16]
        etag = f'W/"{content_hash}"' if self.weak_etags else f'"{content_hash}"'
        
        # Check if client has current version
        if client_etag and self._etags_match(client_etag, etag):
            # Client has current version, return 304 Not Modified
            processing_time = (time.time() - start_time) * 1000
            logger.info(
                "ETag match - 304 Not Modified",
                etag=etag,
                processing_time_ms=f"{processing_time:.2f}",
                path=request.url.path,
                saved_bytes=len(response_body)
            )
            
            return Response(
                status_code=304,
                headers={
                    "etag": etag,
                    "cache-control": "max-age=300, must-revalidate",  # 5 minutes
                    "x-cache-status": "hit"
                }
            )
        
        # Return full response with ETag
        processing_time = (time.time() - start_time) * 1000
        logger.debug(
            "ETag generated",
            etag=etag,
            processing_time_ms=f"{processing_time:.2f}",
            path=request.url.path,
            response_size=len(response_body)
        )
        
        response_headers = dict(response.headers)
        response_headers["etag"] = etag
        response_headers["cache-control"] = "max-age=300, must-revalidate"
        response_headers["x-cache-status"] = "miss"
        
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.media_type
        )
    
    def _etags_match(self, client_etag: str, server_etag: str) -> bool:
        """Check if ETags match, handling weak/strong ETag comparison"""
        
        # Handle multiple ETags in If-None-Match (comma-separated)
        client_etags = [tag.strip() for tag in client_etag.split(',')]
        
        for client_tag in client_etags:
            # Handle wildcard
            if client_tag == '*':
                return True
            
            # Normalize ETags for comparison (remove W/ prefix)
            normalized_client = client_tag.replace('W/', '').strip()
            normalized_server = server_etag.replace('W/', '').strip()
            
            if normalized_client == normalized_server:
                return True
        
        return False


def setup_etag_middleware(app, config: Optional[dict] = None) -> None:
    """Setup ETag middleware with optimal configuration"""
    config = config or {}
    
    middleware_config = {
        "weak_etags": config.get("weak_etags", True),  # Weak ETags for better performance
        "exclude_paths": config.get("exclude_paths", [
            "/health", "/metrics", "/docs", "/openapi.json",
            "/health/ready", "/health/live"
        ])
    }
    
    # Add middleware to FastAPI app
    app.add_middleware(ETagMiddleware, **middleware_config)
    
    logger.info(
        "ETag middleware configured",
        weak_etags=middleware_config["weak_etags"],
        excluded_paths=len(middleware_config["exclude_paths"])
    )