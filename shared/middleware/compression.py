"""
Advanced API Response Compression Middleware
Implements Gzip and Brotli compression with intelligent content-type detection
"""

import gzip
import time
from typing import Any, Dict, List, Optional
import structlog
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False

logger = structlog.get_logger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    High-performance compression middleware with:
    - Brotli and Gzip support
    - Intelligent content-type filtering
    - Size threshold optimization
    - Compression ratio monitoring
    """
    
    def __init__(
        self,
        app: FastAPI,
        minimum_size: int = 500,  # Only compress responses >= 500 bytes
        compression_level: int = 6,  # Good balance of speed vs compression
        exclude_paths: Optional[List[str]] = None,
        exclude_content_types: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        self.exclude_content_types = exclude_content_types or [
            "image/",
            "video/",
            "audio/",
            "application/octet-stream",
            "application/gzip",
            "application/zip"
        ]
        
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and apply compression if beneficial"""
        
        # Skip compression for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Get client compression preferences
        accept_encoding = request.headers.get("accept-encoding", "")
        supports_brotli = "br" in accept_encoding and BROTLI_AVAILABLE
        supports_gzip = "gzip" in accept_encoding
        
        if not (supports_brotli or supports_gzip):
            return await call_next(request)
        
        # Process the request
        start_time = time.time()
        response = await call_next(request)
        
        # Skip compression for non-text content types
        content_type = response.headers.get("content-type", "")
        if any(content_type.startswith(ct) for ct in self.exclude_content_types):
            return response
        
        # Skip compression for small responses
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.minimum_size:
            return response
        
        # Get response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        # Skip compression if body is too small
        if len(response_body) < self.minimum_size:
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        # Choose best compression method
        compressed_body, compression_method = self._compress_body(
            response_body, supports_brotli, supports_gzip
        )
        
        # Calculate compression metrics
        original_size = len(response_body)
        compressed_size = len(compressed_body)
        compression_ratio = (1 - compressed_size / original_size) * 100
        processing_time = (time.time() - start_time) * 1000
        
        # Log compression stats for monitoring
        logger.info(
            "Response compressed",
            method=compression_method,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=f"{compression_ratio:.1f}%",
            processing_time_ms=f"{processing_time:.2f}",
            path=request.url.path
        )
        
        # Create compressed response
        response_headers = dict(response.headers)
        response_headers["content-encoding"] = compression_method
        response_headers["content-length"] = str(compressed_size)
        response_headers["x-compression-ratio"] = f"{compression_ratio:.1f}%"
        
        return Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.media_type
        )
    
    def _compress_body(self, body: bytes, supports_brotli: bool, supports_gzip: bool) -> tuple[bytes, str]:
        """Compress body with best available algorithm"""
        
        if supports_brotli:
            # Brotli typically achieves 20-25% better compression than gzip
            compressed = brotli.compress(
                body, 
                quality=self.compression_level,
                mode=brotli.MODE_TEXT  # Optimized for text/JSON
            )
            return compressed, "br"
        
        elif supports_gzip:
            # Gzip fallback with optimized compression level
            compressed = gzip.compress(body, compresslevel=self.compression_level)
            return compressed, "gzip"
        
        else:
            # Fallback (should not reach here due to earlier checks)
            return body, "identity"


def setup_compression_middleware(app: FastAPI, config: Optional[Dict[str, Any]] = None) -> None:
    """
    Setup compression middleware with optimal configuration
    """
    config = config or {}
    
    # Production-optimized defaults
    middleware_config = {
        "minimum_size": config.get("minimum_size", 500),
        "compression_level": config.get("compression_level", 6),
        "exclude_paths": config.get("exclude_paths", ["/health", "/metrics", "/docs", "/openapi.json"]),
        "exclude_content_types": config.get("exclude_content_types", [
            "image/", "video/", "audio/", "application/octet-stream",
            "application/gzip", "application/zip", "application/pdf"
        ])
    }
    
    # Add middleware to FastAPI app
    app.add_middleware(CompressionMiddleware, **middleware_config)
    
    # Log configuration
    logger.info(
        "Compression middleware configured",
        brotli_available=BROTLI_AVAILABLE,
        minimum_size=middleware_config["minimum_size"],
        compression_level=middleware_config["compression_level"],
        excluded_paths=len(middleware_config["exclude_paths"]),
        excluded_content_types=len(middleware_config["exclude_content_types"])
    )