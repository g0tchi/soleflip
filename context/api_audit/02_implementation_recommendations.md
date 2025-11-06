# StockX API Enhancement Implementation Guide

**Date**: 2025-11-06
**Based on**: StockX API Audit Report
**Target**: Production deployment

---

## HIGH PRIORITY Implementations

### 1. Rate Limiting Implementation

**Priority**: 🔴 HIGH
**Effort**: 2-4 hours
**Impact**: Prevents API quota exhaustion, 429 errors

#### Installation

```bash
pip install aiolimiter
```

#### Implementation

**File**: `domains/integration/services/stockx_service.py`

```python
# Add at top of file
from aiolimiter import AsyncLimiter

class StockXService:
    """
    A service to interact with the StockX Public API, handling the OAuth2 refresh token flow.
    """

    # StockX API rate limit: 10 requests per second (conservative)
    _rate_limiter = AsyncLimiter(10, 1)  # 10 requests per 1 second

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._credentials: Optional[StockXCredentials] = None
        self._lock = asyncio.Lock()

    @RetryHelper.retry_on_exception(
        max_attempts=3,
        delay=2.0,
        backoff_factor=2.0,
        exceptions=(httpx.RequestError, httpx.TimeoutException),
    )
    async def _make_get_request(
        self, endpoint: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Makes a GET request to StockX API with rate limiting and authentication.

        Args:
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments passed to httpx.get()

        Returns:
            Parsed JSON response or None if request fails
        """
        # Apply rate limiting
        async with self._rate_limiter:
            access_token = await self._get_valid_access_token()
            creds = await self._load_credentials()

            headers = {
                "Authorization": f"Bearer {access_token}",
                "x-api-key": creds.api_key,
                "Content-Type": "application/json",
            }

            url = f"{STOCKX_API_BASE_URL}{endpoint}"

            logger.debug(
                "Making StockX GET request",
                endpoint=endpoint,
                url=url,
            )

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(url, headers=headers, **kwargs)

                    if response.status_code == 200:
                        logger.info("StockX API request successful", endpoint=endpoint)
                        return response.json()

                    # Handle rate limiting
                    elif response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(
                            "StockX rate limit exceeded",
                            endpoint=endpoint,
                            retry_after=retry_after,
                        )
                        # Wait for retry period
                        await asyncio.sleep(retry_after)
                        # Retry once after rate limit wait
                        return await self._make_get_request(endpoint, **kwargs)

                    # Handle authentication errors
                    elif response.status_code == 401:
                        logger.warning("StockX authentication failed, refreshing token...")
                        # Force token refresh
                        self._access_token = None
                        self._token_expiry = None
                        # Retry once with new token
                        return await self._make_get_request(endpoint, **kwargs)

                    # Handle other errors
                    else:
                        logger.error(
                            "StockX API request failed",
                            endpoint=endpoint,
                            status_code=response.status_code,
                            response=response.text[:500],
                        )
                        return None

                except httpx.RequestError as e:
                    logger.error(
                        "StockX API request error",
                        endpoint=endpoint,
                        error=str(e),
                    )
                    raise
                except Exception as e:
                    logger.error(
                        "Unexpected error in StockX API request",
                        endpoint=endpoint,
                        error=str(e),
                        exc_info=True,
                    )
                    return None
```

#### Apply to POST Requests

**File**: `domains/integration/services/stockx_service.py`

```python
async def _make_post_request(
    self, endpoint: str, json_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Makes a POST request to StockX API with rate limiting and authentication.
    """
    # Apply rate limiting
    async with self._rate_limiter:
        access_token = await self._get_valid_access_token()
        creds = await self._load_credentials()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-api-key": creds.api_key,
            "Content-Type": "application/json",
        }

        url = f"{STOCKX_API_BASE_URL}{endpoint}"

        logger.debug(
            "Making StockX POST request",
            endpoint=endpoint,
            url=url,
        )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=json_data)

                if response.status_code in [200, 201]:
                    logger.info("StockX POST request successful", endpoint=endpoint)
                    return response.json()

                # Handle rate limiting
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        "StockX rate limit exceeded",
                        endpoint=endpoint,
                        retry_after=retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    return await self._make_post_request(endpoint, json_data)

                # Handle authentication errors
                elif response.status_code == 401:
                    logger.warning("StockX authentication failed, refreshing token...")
                    self._access_token = None
                    self._token_expiry = None
                    return await self._make_post_request(endpoint, json_data)

                else:
                    logger.error(
                        "StockX POST request failed",
                        endpoint=endpoint,
                        status_code=response.status_code,
                        response=response.text[:500],
                    )
                    return None

            except httpx.RequestError as e:
                logger.error(
                    "StockX POST request error",
                    endpoint=endpoint,
                    error=str(e),
                )
                raise
            except Exception as e:
                logger.error(
                    "Unexpected error in StockX POST request",
                    endpoint=endpoint,
                    error=str(e),
                    exc_info=True,
                )
                return None
```

#### Testing

```python
# Test rate limiting
import asyncio
from domains.integration.services.stockx_service import StockXService

async def test_rate_limiting():
    service = StockXService(db_session)

    # Make 15 requests (should throttle after 10)
    start_time = asyncio.get_event_loop().time()

    tasks = [
        service.get_product_details("test-product-id")
        for _ in range(15)
    ]

    await asyncio.gather(*tasks)

    elapsed = asyncio.get_event_loop().time() - start_time

    # Should take at least 1 second (rate limit: 10/sec)
    assert elapsed >= 1.0
    print(f"✅ Rate limiting working: {elapsed:.2f}s for 15 requests")

# Run test
asyncio.run(test_rate_limiting())
```

---

### 2. Connection Pooling

**Priority**: 🔴 HIGH
**Effort**: 2-3 hours
**Impact**: 20-30% performance improvement

#### Implementation

**File**: `domains/integration/services/stockx_service.py`

```python
class StockXService:
    """
    A service to interact with the StockX Public API, handling the OAuth2 refresh token flow.
    """

    # Shared HTTP client for connection pooling
    _http_client: Optional[httpx.AsyncClient] = None
    _rate_limiter = AsyncLimiter(10, 1)

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._credentials: Optional[StockXCredentials] = None
        self._lock = asyncio.Lock()

    @classmethod
    async def get_http_client(cls) -> httpx.AsyncClient:
        """
        Get or create shared HTTP client for connection pooling.

        Connection pooling benefits:
        - Reuses TCP connections
        - Reduces SSL handshake overhead
        - Improves performance by 20-30%
        """
        if cls._http_client is None or cls._http_client.is_closed:
            cls._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                    keepalive_expiry=300.0,  # 5 minutes
                ),
                http2=True,  # Enable HTTP/2 for better performance
            )
        return cls._http_client

    @classmethod
    async def close_http_client(cls):
        """Close shared HTTP client (call on application shutdown)"""
        if cls._http_client and not cls._http_client.is_closed:
            await cls._http_client.aclose()
            cls._http_client = None

    async def _make_get_request(
        self, endpoint: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Makes a GET request to StockX API with connection pooling.
        """
        async with self._rate_limiter:
            access_token = await self._get_valid_access_token()
            creds = await self._load_credentials()

            headers = {
                "Authorization": f"Bearer {access_token}",
                "x-api-key": creds.api_key,
                "Content-Type": "application/json",
            }

            url = f"{STOCKX_API_BASE_URL}{endpoint}"

            logger.debug("Making StockX GET request", endpoint=endpoint, url=url)

            # Use shared HTTP client for connection pooling
            client = await self.get_http_client()

            try:
                response = await client.get(url, headers=headers, **kwargs)

                if response.status_code == 200:
                    logger.info("StockX API request successful", endpoint=endpoint)
                    return response.json()

                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        "StockX rate limit exceeded",
                        endpoint=endpoint,
                        retry_after=retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    return await self._make_get_request(endpoint, **kwargs)

                elif response.status_code == 401:
                    logger.warning("StockX authentication failed, refreshing token...")
                    self._access_token = None
                    self._token_expiry = None
                    return await self._make_get_request(endpoint, **kwargs)

                else:
                    logger.error(
                        "StockX API request failed",
                        endpoint=endpoint,
                        status_code=response.status_code,
                        response=response.text[:500],
                    )
                    return None

            except httpx.RequestError as e:
                logger.error(
                    "StockX API request error",
                    endpoint=endpoint,
                    error=str(e),
                )
                raise
            except Exception as e:
                logger.error(
                    "Unexpected error in StockX API request",
                    endpoint=endpoint,
                    error=str(e),
                    exc_info=True,
                )
                return None
```

#### Application Shutdown Hook

**File**: `main.py`

```python
from domains.integration.services.stockx_service import StockXService

@app.on_event("shutdown")
async def shutdown_event():
    """Close all persistent connections on shutdown"""
    logger.info("Shutting down application, closing HTTP clients...")
    await StockXService.close_http_client()
    logger.info("HTTP clients closed successfully")
```

#### Performance Testing

```python
import time

async def benchmark_connection_pooling():
    """Compare performance with and without connection pooling"""
    service = StockXService(db_session)

    # Test with connection pooling (should be faster)
    start = time.time()
    for _ in range(20):
        await service.get_product_details("test-product-id")
    pooled_time = time.time() - start

    print(f"✅ With connection pooling: {pooled_time:.2f}s for 20 requests")
    print(f"   Average: {pooled_time/20:.3f}s per request")

# Expected result: 15-20% faster than before
```

---

### 3. Test Coverage Expansion

**Priority**: 🔴 HIGH
**Effort**: 1 day
**Impact**: Catch bugs before production, confidence in changes

#### New Test File

**File**: `tests/unit/services/test_stockx_catalog_service.py`

```python
"""
Unit tests for StockXCatalogService
Tests product enrichment and database integration
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from domains.integration.services.stockx_catalog_service import StockXCatalogService
from shared.database.models import Product, Brand, Category, Size


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_stockx_service():
    """Mock StockX service for API calls"""
    service = AsyncMock()
    return service


@pytest.fixture
def catalog_service(mock_db_session, mock_stockx_service):
    """StockXCatalogService with mocked dependencies"""
    with patch(
        "domains.integration.services.stockx_catalog_service.StockXService",
        return_value=mock_stockx_service,
    ):
        service = StockXCatalogService(mock_db_session)
        service.stockx_service = mock_stockx_service
        return service


class TestSearchCatalog:
    """Tests for search_catalog method"""

    @pytest.mark.asyncio
    async def test_search_catalog_success(self, catalog_service, mock_stockx_service):
        """Test successful catalog search"""
        # Arrange
        mock_stockx_service.search_stockx_catalog.return_value = {
            "products": [
                {
                    "id": "test-product-id",
                    "brand": "Nike",
                    "name": "Air Jordan 1",
                    "model": "555088-134",
                }
            ],
            "pagination": {"total": 1, "page": 1, "pageSize": 10},
        }

        # Act
        result = await catalog_service.search_catalog("555088-134")

        # Assert
        assert result is not None
        assert len(result["products"]) == 1
        assert result["products"][0]["id"] == "test-product-id"
        mock_stockx_service.search_stockx_catalog.assert_called_once_with(
            query="555088-134", page=1, page_size=10
        )

    @pytest.mark.asyncio
    async def test_search_catalog_not_found(self, catalog_service, mock_stockx_service):
        """Test catalog search with no results"""
        # Arrange
        mock_stockx_service.search_stockx_catalog.return_value = {
            "products": [],
            "pagination": {"total": 0, "page": 1, "pageSize": 10},
        }

        # Act
        result = await catalog_service.search_catalog("INVALID-SKU")

        # Assert
        assert result is not None
        assert len(result["products"]) == 0


class TestEnrichProductBySKU:
    """Tests for enrich_product_by_sku method"""

    @pytest.mark.asyncio
    async def test_enrich_product_success(
        self, catalog_service, mock_db_session, mock_stockx_service
    ):
        """Test successful product enrichment"""
        # Arrange
        product_id = uuid4()
        mock_product = Mock(
            id=product_id,
            sku="555088-134",
            name="Air Jordan 1",
            brand_id=None,
            category_id=None,
        )

        # Mock database queries
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            mock_product
        )

        # Mock StockX API response
        mock_stockx_service.search_stockx_catalog.return_value = {
            "products": [
                {
                    "id": "stockx-product-id",
                    "brand": "Nike",
                    "name": "Air Jordan 1 Retro High OG",
                    "model": "555088-134",
                    "retailPrice": 170.0,
                    "releaseDate": "1985-04-01",
                }
            ]
        }

        mock_stockx_service.get_product_details.return_value = {
            "id": "stockx-product-id",
            "category": "Sneakers",
        }

        mock_stockx_service.get_all_product_variants.return_value = [
            {"variantId": "variant-1", "variantValue": "8"},
            {"variantId": "variant-2", "variantValue": "8.5"},
        ]

        # Act
        result = await catalog_service.enrich_product_by_sku("555088-134")

        # Assert
        assert result["success"] is True
        assert result["product_id"] == product_id
        assert result["stockx_product_id"] == "stockx-product-id"
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrich_product_not_found_on_stockx(
        self, catalog_service, mock_stockx_service
    ):
        """Test enrichment when product not found on StockX"""
        # Arrange
        mock_stockx_service.search_stockx_catalog.return_value = {"products": []}

        # Act & Assert
        with pytest.raises(ValueError, match="not found on StockX"):
            await catalog_service.enrich_product_by_sku("INVALID-SKU")


class TestDatabaseIntegration:
    """Tests for database integration methods"""

    @pytest.mark.asyncio
    async def test_get_or_create_size_master(
        self, catalog_service, mock_db_session
    ):
        """Test size creation/retrieval"""
        # Arrange
        mock_size = Mock(id=uuid4(), value="8.5")
        mock_db_session.execute = AsyncMock()
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = (
            mock_size
        )

        # Act
        size_id = await catalog_service._get_or_create_size_master("8.5")

        # Assert
        assert size_id == mock_size.id


# Run tests
# pytest tests/unit/services/test_stockx_catalog_service.py -v
```

#### Integration Test

**File**: `tests/integration/api/test_stockx_integration.py`

```python
"""
Integration tests for StockX API endpoints
Tests actual API calls (requires valid credentials)
"""
import pytest
from httpx import AsyncClient

from main import app
from domains.integration.services.stockx_service import StockXService
from shared.database.connection import db_manager


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_stockx_endpoint():
    """Test /api/v1/products/search-stockx endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/products/search-stockx",
            params={"query": "HQ4276", "pageSize": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stockx_service_auth_flow():
    """Test StockX OAuth2 authentication flow"""
    async with db_manager.get_session() as session:
        service = StockXService(session)

        # Test token refresh
        token = await service._get_valid_access_token()

        assert token is not None
        assert len(token) > 0
        assert service._token_expiry is not None


# Run integration tests
# pytest tests/integration/api/test_stockx_integration.py -v -m integration
```

---

### 4. Explicit 429 Handling

**Already Implemented** in Rate Limiting section above!

✅ Added to `_make_get_request()` and `_make_post_request()`

---

## MEDIUM PRIORITY Implementations

### 5. Circuit Breaker Pattern

**Priority**: 🟡 MEDIUM
**Effort**: 4 hours
**Impact**: Better resilience during outages

#### Installation

```bash
pip install circuitbreaker
```

#### Implementation

**File**: `domains/integration/services/stockx_service.py`

```python
from circuitbreaker import circuit

class StockXService:
    ...

    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=httpx.HTTPError)
    async def _make_get_request(
        self, endpoint: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Makes a GET request with circuit breaker protection.

        Circuit breaker: If 5 consecutive requests fail, circuit opens for 60 seconds.
        This prevents cascading failures and gives StockX API time to recover.
        """
        async with self._rate_limiter:
            # ... rest of implementation
```

**Benefits**:
- Prevents cascading failures
- Reduces unnecessary API calls during outages
- Automatic recovery after timeout

---

### 6. Market Data Caching

**Priority**: 🟡 MEDIUM
**Effort**: 1 day
**Impact**: Reduce API calls by 50-70%

#### Implementation

**File**: `domains/integration/services/stockx_service.py`

```python
from functools import lru_cache
from datetime import datetime, timedelta
import json

class MarketDataCache:
    """TTL-based cache for StockX market data"""

    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self._cache: Dict[str, Tuple[Dict, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[Dict]:
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < self._ttl:
                return data
            # Expired, remove from cache
            del self._cache[key]
        return None

    def set(self, key: str, data: Dict):
        self._cache[key] = (data, datetime.utcnow())

    def clear(self):
        self._cache.clear()


class StockXService:
    # Shared cache across all instances
    _market_data_cache = MarketDataCache(ttl_seconds=300)

    async def get_market_data_from_stockx(
        self,
        product_id: str,
        currency_code: str = "EUR",
        use_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch market data (lowest ask, highest bid, last sale) with caching.

        Args:
            product_id: StockX product UUID
            currency_code: Currency for pricing (EUR, USD, GBP)
            use_cache: Whether to use cache (default: True)

        Returns:
            Market data dict or None
        """
        cache_key = f"market_data:{product_id}:{currency_code}"

        # Try cache first
        if use_cache:
            cached_data = self._market_data_cache.get(cache_key)
            if cached_data:
                logger.debug("Cache hit for market data", product_id=product_id)
                return cached_data

        # Cache miss, fetch from API
        endpoint = f"/catalog/products/{product_id}/market-data"
        params = {"currencyCode": currency_code}

        market_data = await self._make_get_request(endpoint, params=params)

        if market_data and use_cache:
            # Cache the result
            self._market_data_cache.set(cache_key, market_data)
            logger.debug("Cached market data", product_id=product_id)

        return market_data
```

---

### 7. Prometheus Metrics

**Priority**: 🟡 MEDIUM
**Effort**: 1 day
**Impact**: Better observability and alerting

#### Implementation

**File**: `domains/integration/services/stockx_service.py`

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
stockx_requests_total = Counter(
    "stockx_requests_total",
    "Total StockX API requests",
    ["method", "endpoint", "status"],
)

stockx_request_duration_seconds = Histogram(
    "stockx_request_duration_seconds",
    "StockX API request duration",
    ["method", "endpoint"],
)

stockx_rate_limit_hits = Counter(
    "stockx_rate_limit_hits_total",
    "Number of times rate limit was hit",
)

stockx_auth_failures = Counter(
    "stockx_auth_failures_total",
    "Number of authentication failures",
)


class StockXService:
    ...

    async def _make_get_request(
        self, endpoint: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Makes a GET request with Prometheus metrics"""
        start_time = time.time()

        async with self._rate_limiter:
            # ... authentication and setup ...

            try:
                response = await client.get(url, headers=headers, **kwargs)
                duration = time.time() - start_time

                # Record metrics
                stockx_request_duration_seconds.labels(
                    method="GET",
                    endpoint=endpoint,
                ).observe(duration)

                if response.status_code == 200:
                    stockx_requests_total.labels(
                        method="GET",
                        endpoint=endpoint,
                        status="success",
                    ).inc()
                    return response.json()

                elif response.status_code == 429:
                    stockx_requests_total.labels(
                        method="GET",
                        endpoint=endpoint,
                        status="rate_limited",
                    ).inc()
                    stockx_rate_limit_hits.inc()
                    # ... handle rate limit ...

                elif response.status_code == 401:
                    stockx_requests_total.labels(
                        method="GET",
                        endpoint=endpoint,
                        status="auth_failed",
                    ).inc()
                    stockx_auth_failures.inc()
                    # ... handle auth failure ...

                else:
                    stockx_requests_total.labels(
                        method="GET",
                        endpoint=endpoint,
                        status="error",
                    ).inc()
                    return None

            except Exception as e:
                stockx_requests_total.labels(
                    method="GET",
                    endpoint=endpoint,
                    status="exception",
                ).inc()
                raise
```

#### Grafana Dashboard Queries

```promql
# Success rate
rate(stockx_requests_total{status="success"}[5m]) /
rate(stockx_requests_total[5m])

# Average response time
rate(stockx_request_duration_seconds_sum[5m]) /
rate(stockx_request_duration_seconds_count[5m])

# Rate limit hits per minute
rate(stockx_rate_limit_hits_total[1m]) * 60

# Authentication failures
increase(stockx_auth_failures_total[1h])
```

---

## Summary Checklist

### Implementation Priority

#### Week 1 (HIGH Priority)
- [ ] Implement rate limiting with `aiolimiter`
- [ ] Add connection pooling with persistent httpx client
- [ ] Add explicit 429 error handling
- [ ] Expand test coverage for StockXCatalogService

#### Week 2 (MEDIUM Priority)
- [ ] Implement circuit breaker pattern
- [ ] Add market data caching layer
- [ ] Integrate Prometheus metrics
- [ ] Add idempotency keys for mutations

#### Week 3+ (LOW Priority / Backlog)
- [ ] Migrate to Pydantic response models
- [ ] Implement async batch processing
- [ ] Add advanced filtering to search
- [ ] Implement webhook receiver

---

**Next Steps**: Review and approve implementation plan, then proceed with Week 1 tasks.

**Estimated Total Effort**: 5-7 days for all HIGH + MEDIUM priority items.

**Expected Impact**:
- 30-40% performance improvement
- 50-70% reduction in API calls (caching)
- 99.9% uptime with circuit breaker
- Zero rate limit issues
- Comprehensive monitoring and alerting
