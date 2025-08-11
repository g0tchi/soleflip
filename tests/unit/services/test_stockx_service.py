import pytest
import httpx
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from domains.integration.services.stockx_service import StockXService, StockXCredentials
from shared.database.models import SystemConfig

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def stockx_service():
    """Provides an instance of the StockXService for testing."""
    return StockXService()

@pytest.fixture
def mock_db_session():
    """Mocks the database session and yields it."""
    mock_session = AsyncMock()
    # Mock the context manager
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
    # The get_value method is synchronous
    config.get_value = MagicMock(return_value=value)
    return config

async def test_get_credentials_success(stockx_service, mock_db_session):
    """
    Tests that credentials are fetched and decoded correctly from the database.
    """
    # Arrange
    mock_api_key_config = _create_mock_config("stockx_api_key", "test_api_key")
    mock_jwt_config = _create_mock_config("stockx_jwt_token", "test_jwt")

    # The result of `await session.execute()` is a synchronous object.
    # So the side_effect should return a MagicMock, not an AsyncMock.
    def execute_side_effect(query):
        query_str = str(query.compile(compile_kwargs={"literal_binds": True}))
        mock_result = MagicMock()
        if "stockx_api_key" in query_str:
            mock_result.scalar_one_or_none.return_value = mock_api_key_config
        elif "stockx_jwt_token" in query_str:
            mock_result.scalar_one_or_none.return_value = mock_jwt_config
        else:
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db_session.execute.side_effect = execute_side_effect

    # Act
    credentials = await stockx_service._get_credentials()

    # Assert
    assert isinstance(credentials, StockXCredentials)
    assert credentials.api_key == "test_api_key"
    assert credentials.jwt_token == "test_jwt"
    assert mock_db_session.execute.call_count == 2

async def test_get_credentials_missing_key(stockx_service, mock_db_session):
    """
    Tests that a ValueError is raised if the API key is not found in the database.
    """
    # Arrange
    def execute_side_effect(query):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db_session.execute.side_effect = execute_side_effect

    # Act & Assert
    with pytest.raises(ValueError, match="StockX API key .* not configured"):
        await stockx_service._get_credentials()

async def test_get_historical_orders_success_single_page(stockx_service):
    """
    Tests successfully fetching orders from a single page of the StockX API.
    """
    with patch.object(stockx_service, '_get_credentials', new_callable=AsyncMock) as mock_get_creds, \
         patch('domains.integration.services.stockx_service.httpx.AsyncClient') as MockAsyncClient:

        # Arrange
        mock_get_creds.return_value = StockXCredentials("key", "jwt")

        mock_response = httpx.Response(
            200,
            json={"orders": [{"id": 1}, {"id": 2}], "hasNextPage": False},
            request=httpx.Request("GET", "/selling/orders/history")
        )
        mock_instance = MockAsyncClient.return_value.__aenter__.return_value
        mock_instance.get.return_value = mock_response

        # Act
        from_date = date(2023, 1, 1)
        to_date = date(2023, 1, 31)
        orders = await stockx_service.get_historical_orders(from_date, to_date)

        # Assert
        assert len(orders) == 2
        assert orders[0]["id"] == 1
        mock_instance.get.assert_called_once()
        get_call_args = mock_instance.get.call_args
        assert get_call_args.kwargs['params']['pageNumber'] == 1


async def test_get_historical_orders_success_multiple_pages(stockx_service):
    """
    Tests successfully fetching orders across multiple pages from the StockX API.
    """
    with patch.object(stockx_service, '_get_credentials', new_callable=AsyncMock) as mock_get_creds, \
         patch('domains.integration.services.stockx_service.httpx.AsyncClient') as MockAsyncClient:

        # Arrange
        mock_get_creds.return_value = StockXCredentials("key", "jwt")

        request = httpx.Request("GET", "/selling/orders/history")
        response1 = httpx.Response(200, json={"orders": [{"id": 1}], "hasNextPage": True}, request=request)
        response2 = httpx.Response(200, json={"orders": [{"id": 2}], "hasNextPage": False}, request=request)

        mock_instance = MockAsyncClient.return_value.__aenter__.return_value
        mock_instance.get.side_effect = [response1, response2]

        # Act
        from_date = date(2023, 1, 1)
        to_date = date(2023, 1, 31)
        orders = await stockx_service.get_historical_orders(from_date, to_date)

        # Assert
        assert len(orders) == 2
        assert orders[0]["id"] == 1
        assert orders[1]["id"] == 2
        assert mock_instance.get.call_count == 2

async def test_get_historical_orders_api_error(stockx_service):
    """
    Tests that an HTTP error from the API is properly raised.
    """
    with patch.object(stockx_service, '_get_credentials', new_callable=AsyncMock) as mock_get_creds, \
         patch('domains.integration.services.stockx_service.httpx.AsyncClient') as MockAsyncClient:

        # Arrange
        mock_get_creds.return_value = StockXCredentials("key", "jwt")

        mock_response = httpx.Response(
            401,
            json={"error": "Unauthorized"},
            request=httpx.Request("GET", "/selling/orders/history")
        )
        mock_instance = MockAsyncClient.return_value.__aenter__.return_value
        mock_instance.get.return_value = mock_response

        # Act & Assert
        from_date = date(2023, 1, 1)
        to_date = date(2023, 1, 31)
        with pytest.raises(httpx.HTTPStatusError):
            await stockx_service.get_historical_orders(from_date, to_date)
