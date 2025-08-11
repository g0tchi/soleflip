import pytest
import httpx
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from domains.integration.services.stockx_service import StockXService, StockXCredentials
from shared.database.models import SystemConfig

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def stockx_service():
    """Provides a new instance of the StockXService for each test."""
    return StockXService()

@pytest.fixture
def mock_db_session():
    """Mocks the database session and yields it."""
    mock_session = AsyncMock()
    async def __aenter__(*args, **kwargs):
        return mock_session
    async def __aexit__(*args, **kwargs):
        pass

    db_manager_mock = MagicMock()
    db_manager_mock.get_session.return_value.__aenter__ = __aenter__
    db_manager_mock.get_session.return_value.__aexit__ = __aexit__

    with patch('domains.integration.services.stockx_service.db_manager', db_manager_mock):
        yield mock_session

def _create_mock_config(key, value):
    """Helper to create a mock SystemConfig object."""
    config = SystemConfig(key=key)
    config.get_value = MagicMock(return_value=value)
    return config

async def test_load_credentials_success(stockx_service, mock_db_session):
    """
    Tests that all required credentials are fetched and loaded correctly.
    """
    # Arrange
    mock_configs = [
        _create_mock_config("stockx_client_id", "test_client_id"),
        _create_mock_config("stockx_client_secret", "test_client_secret"),
        _create_mock_config("stockx_refresh_token", "test_refresh_token"),
        _create_mock_config("stockx_api_key", "test_api_key"),
    ]

    # `await session.execute()` returns a Result object (sync).
    # `Result.scalars()` returns a ScalarResult (sync, iterable).
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_configs
    mock_db_session.execute.return_value = mock_result

    # Act
    credentials = await stockx_service._load_credentials()

    # Assert
    assert isinstance(credentials, StockXCredentials)
    assert credentials.client_id == "test_client_id"
    assert credentials.refresh_token == "test_refresh_token"
    assert credentials.api_key == "test_api_key"
    mock_db_session.execute.assert_called_once()

async def test_load_credentials_missing_key(stockx_service, mock_db_session):
    """
    Tests that a ValueError is raised if a required credential is missing.
    """
    # Arrange
    mock_configs = [_create_mock_config("stockx_client_id", "test_client_id")]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_configs
    mock_db_session.execute.return_value = mock_result

    # Act & Assert
    with pytest.raises(ValueError, match="Missing required StockX credential in system_config: stockx_client_secret"):
        await stockx_service._load_credentials()

async def test_refresh_access_token_success(stockx_service):
    """
    Tests the successful renewal of an access token.
    """
    # Arrange
    with patch.object(stockx_service, '_load_credentials', new_callable=AsyncMock) as mock_load_creds, \
         patch('httpx.AsyncClient') as MockAsyncClient:

        mock_load_creds.return_value = StockXCredentials("id", "secret", "refresh", "api_key")

        mock_response = httpx.Response(
            200,
            json={"access_token": "new_access_token", "expires_in": 3600},
            request=httpx.Request("POST", "https://accounts.stockx.com/oauth/token")
        )
        mock_instance = MockAsyncClient.return_value.__aenter__.return_value
        mock_instance.post.return_value = mock_response

        # Act
        await stockx_service._refresh_access_token()

        # Assert
        assert stockx_service._access_token == "new_access_token"
        assert stockx_service._token_expiry > datetime.now(timezone.utc)
        mock_instance.post.assert_called_once()
        post_args = mock_instance.post.call_args
        assert post_args.args[0] == "https://accounts.stockx.com/oauth/token"
        assert post_args.kwargs['data']['grant_type'] == "refresh_token"

async def test_get_valid_access_token_uses_cache(stockx_service):
    """
    Tests that a valid, cached token is returned without a refresh call.
    """
    # Arrange
    stockx_service._access_token = "cached_token"
    stockx_service._token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    with patch.object(stockx_service, '_refresh_access_token', new_callable=AsyncMock) as mock_refresh:
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

    with patch.object(stockx_service, '_refresh_access_token', new_callable=AsyncMock) as mock_refresh:
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
    with patch.object(stockx_service, '_make_paginated_get_request', new_callable=AsyncMock) as mock_paginated_get:
        mock_paginated_get.return_value = [{"id": "active_order_1"}]

        # Act
        orders = await stockx_service.get_active_orders(orderStatus="SHIPPED")

        # Assert
        assert len(orders) == 1
        assert orders[0]["id"] == "active_order_1"
        mock_paginated_get.assert_called_once_with(
            "/selling/orders/active",
            {"orderStatus": "SHIPPED"}
        )
