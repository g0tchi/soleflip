import pytest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from domains.integration.services.stockx_service import StockXService, StockXCredentials
from shared.database.models import SystemConfig

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    """Creates a mock of an async SQLAlchemy session."""
    session = AsyncMock()
    # `execute` should return an object that has a `scalars` method,
    # which in turn is iterable.
    mock_result = MagicMock()
    session.execute.return_value = mock_result
    return session, mock_result


@pytest.fixture
def stockx_service(mock_db_session):
    """Provides a new instance of the StockXService with a mocked db_session."""
    session, _ = mock_db_session
    return StockXService(db_session=session)


def _create_mock_config(key, value):
    """Helper to create a mock SystemConfig object."""
    config = SystemConfig(key=key)
    # Mock the instance method `get_value` on the object
    config.get_value = MagicMock(return_value=value)
    return config


async def test_load_credentials_success(stockx_service, mock_db_session):
    """
    Tests that all required credentials are fetched and loaded correctly.
    """
    # Arrange
    session, mock_result = mock_db_session
    mock_configs = [
        _create_mock_config("stockx_client_id", "test_client_id"),
        _create_mock_config("stockx_client_secret", "test_client_secret"),
        _create_mock_config("stockx_refresh_token", "test_refresh_token"),
        _create_mock_config("stockx_api_key", "test_api_key"),
    ]
    mock_result.scalars.return_value = mock_configs

    # Act
    credentials = await stockx_service._load_credentials()

    # Assert
    assert isinstance(credentials, StockXCredentials)
    assert credentials.client_id == "test_client_id"
    assert credentials.refresh_token == "test_refresh_token"
    assert credentials.api_key == "test_api_key"
    session.execute.assert_called_once()


async def test_load_credentials_missing_key(stockx_service, mock_db_session):
    """
    Tests that a ValueError is raised if a required credential is missing.
    """
    # Arrange
    _, mock_result = mock_db_session
    mock_configs = [_create_mock_config("stockx_client_id", "test_client_id")]
    mock_result.scalars.return_value = mock_configs

    # Act & Assert
    with pytest.raises(
        ValueError,
        match="Missing required StockX credential in system_config: stockx_client_secret",
    ):
        await stockx_service._load_credentials()


async def test_refresh_access_token_success(stockx_service):
    """
    Tests the successful renewal of an access token.
    """
    # Arrange
    # We patch _load_credentials because its testing is separate.
    with (
        patch.object(
            stockx_service, "_load_credentials", new_callable=AsyncMock
        ) as mock_load_creds,
        patch("httpx.AsyncClient") as MockAsyncClient,
    ):

        mock_load_creds.return_value = StockXCredentials("id", "secret", "refresh", "api_key")

        # Mock the response from the httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new_access_token", "expires_in": 3600}

        mock_instance = MockAsyncClient.return_value.__aenter__.return_value
        mock_instance.post.return_value = mock_response

        # Act
        await stockx_service._refresh_access_token()

        # Assert
        assert stockx_service._access_token == "new_access_token"
        assert stockx_service._token_expiry > datetime.now(timezone.utc)
        mock_instance.post.assert_called_once()
        post_args = mock_instance.post.call_args
        assert post_args.kwargs["data"]["grant_type"] == "refresh_token"


async def test_get_valid_access_token_uses_cache(stockx_service):
    """
    Tests that a valid, cached token is returned without a refresh call.
    """
    # Arrange
    stockx_service._access_token = "cached_token"
    stockx_service._token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    with patch.object(
        stockx_service, "_refresh_access_token", new_callable=AsyncMock
    ) as mock_refresh:
        # Act
        token = await stockx_service._get_valid_access_token()

        # Assert
        assert token == "cached_token"
        mock_refresh.assert_not_called()


async def test_get_valid_access_token_refreshes_expired_token(stockx_service):
    """
    Tests that an expired token triggers a refresh.
    """
    # Arrange
    stockx_service._access_token = "expired_token"
    stockx_service._token_expiry = datetime.now(timezone.utc) - timedelta(hours=1)

    with patch.object(
        stockx_service, "_refresh_access_token", new_callable=AsyncMock
    ) as mock_refresh:
        # We need to set the token inside the mock, because the original is expired
        async def side_effect():
            stockx_service._access_token = "refreshed_token"

        mock_refresh.side_effect = side_effect

        # Act
        token = await stockx_service._get_valid_access_token()

        # Assert
        assert token == "refreshed_token"
        mock_refresh.assert_called_once()


async def test_get_active_orders_success(stockx_service):
    """
    Tests successfully fetching active orders.
    """
    # Arrange
    with patch.object(
        stockx_service, "_make_paginated_get_request", new_callable=AsyncMock
    ) as mock_paginated_get:
        mock_paginated_get.return_value = [{"id": "active_order_1"}]

        # Act
        orders = await stockx_service.get_active_orders(orderStatus="SHIPPED")

        # Assert
        assert len(orders) == 1
        assert orders[0]["id"] == "active_order_1"
        mock_paginated_get.assert_called_once_with(
            "/selling/orders/active", {"orderStatus": "SHIPPED"}, "orders"
        )


async def test_get_product_details_success(stockx_service):
    """
    Tests successfully fetching product details.
    """
    # Arrange
    with patch.object(stockx_service, "_make_get_request", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"productId": "product123", "title": "Test Product"}
        product_id = "product123"

        # Act
        details = await stockx_service.get_product_details(product_id)

        # Assert
        assert details is not None
        assert details["title"] == "Test Product"
        mock_get.assert_called_once_with(f"/catalog/products/{product_id}")


async def test_get_product_details_not_found(stockx_service):
    """
    Tests handling of a 404 Not Found error when fetching product details.
    """
    # Arrange
    import httpx

    with patch.object(stockx_service, "_make_get_request", new_callable=AsyncMock) as mock_get:
        # Simulate the HTTP client raising a 404 error
        mock_get.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        product_id = "nonexistent_product"

        # Act
        details = await stockx_service.get_product_details(product_id)

        # Assert
        assert details is None
        mock_get.assert_called_once_with(f"/catalog/products/{product_id}")


async def test_get_all_product_variants_success(stockx_service):
    """
    Tests successfully fetching all product variants.
    """
    # Arrange
    with patch.object(stockx_service, "_make_get_request", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [{"variantId": "variant1"}, {"variantId": "variant2"}]
        product_id = "product123"

        # Act
        variants = await stockx_service.get_all_product_variants(product_id)

        # Assert
        assert len(variants) == 2
        assert variants[0]["variantId"] == "variant1"
        mock_get.assert_called_once_with(f"/catalog/products/{product_id}/variants")


async def test_get_all_product_variants_not_found(stockx_service):
    """
    Tests handling of a 404 Not Found error when fetching product variants.
    """
    # Arrange
    import httpx

    with patch.object(stockx_service, "_make_get_request", new_callable=AsyncMock) as mock_get:
        # Simulate the HTTP client raising a 404 error
        mock_get.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        product_id = "nonexistent_product"

        # Act
        variants = await stockx_service.get_all_product_variants(product_id)

        # Assert
        assert variants == []
        mock_get.assert_called_once_with(f"/catalog/products/{product_id}/variants")


async def test_get_all_listings_success(stockx_service):
    """
    Tests successfully fetching all listings.
    """
    # Arrange
    with patch.object(
        stockx_service, "_make_paginated_get_request", new_callable=AsyncMock
    ) as mock_paginated_get:
        mock_paginated_get.return_value = [{"listingId": "listing1"}]

        # Act
        listings = await stockx_service.get_all_listings(listingStatuses="ACTIVE")

        # Assert
        assert len(listings) == 1
        assert listings[0]["listingId"] == "listing1"
        mock_paginated_get.assert_called_once_with(
            "/selling/listings", {"listingStatuses": "ACTIVE"}, "listings"
        )


async def test_get_order_details_success(stockx_service):
    """
    Tests successfully fetching order details.
    """
    # Arrange
    with patch.object(stockx_service, "_make_get_request", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"orderNumber": "123-456", "status": "SHIPPED"}
        order_number = "123-456"

        # Act
        details = await stockx_service.get_order_details(order_number)

        # Assert
        assert details is not None
        assert details["status"] == "SHIPPED"
        mock_get.assert_called_once_with(f"/selling/orders/{order_number}")


async def test_get_order_details_not_found(stockx_service):
    """
    Tests handling of a 404 Not Found error when fetching order details.
    """
    # Arrange
    import httpx

    with patch.object(stockx_service, "_make_get_request", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        order_number = "nonexistent_order"

        # Act
        details = await stockx_service.get_order_details(order_number)

        # Assert
        assert details is None
        mock_get.assert_called_once_with(f"/selling/orders/{order_number}")


async def test_get_shipping_document_success(stockx_service):
    """
    Tests successfully fetching a shipping document.
    """
    # Arrange
    with patch.object(
        stockx_service, "_make_get_request_for_binary", new_callable=AsyncMock
    ) as mock_get_binary:
        mock_get_binary.return_value = b"%PDF-1.4..."
        order_number = "123-456"
        shipping_id = "789"

        # Act
        pdf_bytes = await stockx_service.get_shipping_document(order_number, shipping_id)

        # Assert
        assert pdf_bytes is not None
        assert pdf_bytes == b"%PDF-1.4..."
        mock_get_binary.assert_called_once_with(
            f"/selling/orders/{order_number}/shipping-document/{shipping_id}"
        )


async def test_get_shipping_document_not_found(stockx_service):
    """
    Tests handling of a 404 Not Found error when fetching a shipping document.
    """
    # Arrange
    import httpx

    with patch.object(
        stockx_service, "_make_get_request_for_binary", new_callable=AsyncMock
    ) as mock_get_binary:
        mock_get_binary.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        order_number = "123-456"
        shipping_id = "nonexistent_shipping_id"

        # Act
        pdf_bytes = await stockx_service.get_shipping_document(order_number, shipping_id)

        # Assert
        assert pdf_bytes is None
        mock_get_binary.assert_called_once_with(
            f"/selling/orders/{order_number}/shipping-document/{shipping_id}"
        )
