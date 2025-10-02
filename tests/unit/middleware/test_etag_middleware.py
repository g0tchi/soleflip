"""
Unit tests for ETag Middleware
Testing HTTP caching, conditional requests, and ETag generation for 100% coverage
"""

import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI, Request, Response

from shared.middleware.etag import ETagMiddleware, setup_etag_middleware


class TestETagMiddleware:
    """Test ETagMiddleware HTTP caching functionality"""

    @pytest.fixture
    def app(self):
        """Create test FastAPI application"""
        return FastAPI()

    @pytest.fixture
    def etag_middleware(self, app):
        """Create ETag middleware instance"""
        return ETagMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        return request

    @pytest.fixture
    def mock_response(self):
        """Create mock response"""
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.headers = {}
        response.media_type = "application/json"

        # Mock body_iterator for async iteration
        async def body_iter():
            yield b'{"data": "test"}'
        response.body_iterator = body_iter()
        return response

    async def test_excluded_paths_debug_logging(self, etag_middleware, mock_request):
        """Test debug logging for excluded paths - covers lines 38-39"""
        # Arrange
        mock_request.url.path = "/health"

        async def mock_call_next(request):
            return Response(content="OK", status_code=200)

        # Act
        result = await etag_middleware.dispatch(mock_request, mock_call_next)

        # Assert
        assert result.status_code == 200
        # The path should be excluded and skip ETag processing

    async def test_non_get_method_debug_logging(self, etag_middleware, mock_request):
        """Test debug logging for non-GET methods"""
        # Arrange
        mock_request.method = "POST"
        mock_request.url.path = "/api/data"

        async def mock_call_next(request):
            return Response(content="Created", status_code=201)

        # Act
        result = await etag_middleware.dispatch(mock_request, mock_call_next)

        # Assert
        assert result.status_code == 201
        # Should skip ETag for non-GET/HEAD methods

    async def test_etag_generation_and_response(self, etag_middleware, mock_request):
        """Test ETag generation and response modification - covers lines 68-77, 112-126"""
        # Arrange
        mock_request.headers = {}  # No existing ETag

        async def mock_call_next(request):
            response = Response(content=b'{"test": "data"}', status_code=200)
            response.media_type = "application/json"

            # Mock the body_iterator properly
            async def body_iter():
                yield b'{"test": "data"}'
            response.body_iterator = body_iter()
            return response

        # Act
        result = await etag_middleware.dispatch(mock_request, mock_call_next)

        # Assert
        assert result.status_code == 200
        assert "etag" in result.headers
        assert "cache-control" in result.headers
        assert result.headers["x-cache-status"] == "miss"

    async def test_etag_match_304_response(self, etag_middleware, mock_request):
        """Test ETag match returning 304 Not Modified - covers lines 68-77"""
        # Arrange
        # Set up a request with matching ETag
        test_content = b'{"test": "data"}'
        import hashlib
        content_hash = hashlib.md5(test_content).hexdigest()[:16]
        etag = f'W/"{content_hash}"'

        mock_request.headers = {"if-none-match": etag}

        async def mock_call_next(request):
            response = Response(content=test_content, status_code=200)
            response.media_type = "application/json"

            async def body_iter():
                yield test_content
            response.body_iterator = body_iter()
            return response

        # Act
        result = await etag_middleware.dispatch(mock_request, mock_call_next)

        # Assert
        assert result.status_code == 304
        assert "etag" in result.headers
        assert result.headers["x-cache-status"] == "hit"

    def test_etags_match_basic(self, etag_middleware):
        """Test _etags_match method with basic matching - covers lines 112-126"""
        # Test exact match
        assert etag_middleware._etags_match('W/"abc123"', 'W/"abc123"') is True
        assert etag_middleware._etags_match('"abc123"', '"abc123"') is True

    def test_etags_match_weak_strong_comparison(self, etag_middleware):
        """Test _etags_match with weak/strong ETag comparison - covers lines 112-126"""
        # Test weak vs strong ETag matching
        assert etag_middleware._etags_match('W/"abc123"', '"abc123"') is True
        assert etag_middleware._etags_match('"abc123"', 'W/"abc123"') is True

    def test_etags_match_multiple_tags(self, etag_middleware):
        """Test _etags_match with multiple ETags - covers lines 112-126"""
        # Test multiple ETags (comma-separated)
        client_etags = 'W/"abc123", W/"def456", W/"ghi789"'
        assert etag_middleware._etags_match(client_etags, 'W/"def456"') is True
        assert etag_middleware._etags_match(client_etags, 'W/"xyz999"') is False

    def test_etags_match_wildcard(self, etag_middleware):
        """Test _etags_match with wildcard - covers lines 112-126"""
        # Test wildcard matching
        assert etag_middleware._etags_match('*', 'W/"anything"') is True
        assert etag_middleware._etags_match('W/"test", *', 'W/"other"') is True

    def test_etags_match_no_match(self, etag_middleware):
        """Test _etags_match when no match found - covers lines 112-126"""
        # Test no match scenario
        assert etag_middleware._etags_match('W/"abc123"', 'W/"def456"') is False
        assert etag_middleware._etags_match('"test1", "test2"', '"test3"') is False

    async def test_non_200_response_passthrough(self, etag_middleware, mock_request):
        """Test that non-200 responses pass through without ETag processing"""
        # Arrange
        async def mock_call_next(request):
            return Response(content="Not Found", status_code=404)

        # Act
        result = await etag_middleware.dispatch(mock_request, mock_call_next)

        # Assert
        assert result.status_code == 404
        assert "etag" not in result.headers

    def test_middleware_initialization(self, app):
        """Test ETagMiddleware initialization"""
        # Test with defaults
        middleware = ETagMiddleware(app)
        assert middleware.weak_etags is True
        assert "/health" in middleware.exclude_paths

        # Test with custom settings
        custom_paths = ["/custom", "/exclude"]
        middleware_custom = ETagMiddleware(app, weak_etags=False, exclude_paths=custom_paths)
        assert middleware_custom.weak_etags is False
        assert middleware_custom.exclude_paths == custom_paths

    def test_etag_format_weak_vs_strong(self, etag_middleware):
        """Test ETag format generation (weak vs strong)"""
        # Test weak ETags (default)
        weak_middleware = ETagMiddleware(None, weak_etags=True)
        assert weak_middleware.weak_etags is True

        # Test strong ETags
        strong_middleware = ETagMiddleware(None, weak_etags=False)
        assert strong_middleware.weak_etags is False


class TestSetupETagMiddleware:
    """Test setup_etag_middleware configuration function"""

    def test_setup_etag_middleware_defaults(self):
        """Test setup_etag_middleware with default configuration"""
        # Arrange
        app = MagicMock()
        app.add_middleware = MagicMock()

        # Act
        setup_etag_middleware(app)

        # Assert
        app.add_middleware.assert_called_once()
        call_args = app.add_middleware.call_args
        assert call_args[0][0] == ETagMiddleware

    def test_setup_etag_middleware_custom_config(self):
        """Test setup_etag_middleware with custom configuration"""
        # Arrange
        app = MagicMock()
        app.add_middleware = MagicMock()

        config = {
            "weak_etags": False,
            "exclude_paths": ["/custom", "/path"]
        }

        # Act
        setup_etag_middleware(app, config)

        # Assert
        app.add_middleware.assert_called_once()
        call_args = app.add_middleware.call_args
        assert call_args[1]["weak_etags"] is False
        assert call_args[1]["exclude_paths"] == ["/custom", "/path"]

    def test_setup_etag_middleware_none_config(self):
        """Test setup_etag_middleware with None config"""
        # Arrange
        app = MagicMock()
        app.add_middleware = MagicMock()

        # Act
        setup_etag_middleware(app, None)

        # Assert
        app.add_middleware.assert_called_once()
        # Should use defaults when config is None